"""
Call Analysts Dispatcher — Node 2

Routes each classified call to the appropriate analyst and aggregates results.
Runs analyses sequentially to avoid API rate limits.
"""

import structlog
from ...state import SBITISState
from ...schemas.call_classification import CallType, ClassifiedCall
from .strategy_analyst import analyze_strategy_call
from .training_analyst import analyze_sales_training
from .leadership_analyst import analyze_leadership_meeting
from .team_meeting_analyst import analyze_team_meeting
from .client_review_analyst import analyze_client_review
from .partnership_analyst import analyze_partnership_meeting

log = structlog.get_logger(__name__)

_ANALYST_MAP = {
    CallType.STRATEGY_CALL: analyze_strategy_call,
    CallType.SALES_TRAINING: analyze_sales_training,
    CallType.LEADERSHIP_MEETING: analyze_leadership_meeting,
    CallType.TEAM_MEETING: analyze_team_meeting,
    CallType.CLIENT_REVIEW: analyze_client_review,
    CallType.PARTNERSHIP_MEETING: analyze_partnership_meeting,
}


def call_analysts_node(state: SBITISState) -> dict:
    """
    LangGraph node: Dispatches each classified call to the correct analyst.
    Skips APPOINTMENT_SETTING calls. Accumulates results by type.
    """
    log.info("node.call_analysts.start", total=len(state.get("classified_calls", [])))

    strategy = []
    training = []
    leadership = []
    team = []
    client_review = []
    partnership = []
    skipped = []
    errors = []

    for call in state.get("classified_calls") or []:
        call_type = call.call_type

        # Skip appointment setting — no deep analysis needed
        if call_type == CallType.APPOINTMENT_SETTING or call.skip_deep_analysis:
            skipped.append(call.file_id)
            log.info("node.call_analysts.skipped", file_id=call.file_id, reason="appointment_setting")
            continue

        analyst_fn = _ANALYST_MAP.get(call_type)
        if not analyst_fn:
            skipped.append(call.file_id)
            log.warning("node.call_analysts.no_analyst", file_id=call.file_id, call_type=call_type.value)
            continue

        result = analyst_fn(call)

        if result is None:
            errors.append(f"Analyst returned None for {call.file_id} ({call_type.value})")
            continue

        if call_type == CallType.STRATEGY_CALL:
            strategy.append(result)
        elif call_type == CallType.SALES_TRAINING:
            training.append(result)
        elif call_type == CallType.LEADERSHIP_MEETING:
            leadership.append(result)
        elif call_type == CallType.TEAM_MEETING:
            team.append(result)
        elif call_type == CallType.CLIENT_REVIEW:
            client_review.append(result)
        elif call_type == CallType.PARTNERSHIP_MEETING:
            partnership.append(result)

    log.info(
        "node.call_analysts.done",
        strategy=len(strategy),
        training=len(training),
        leadership=len(leadership),
        team=len(team),
        client_review=len(client_review),
        partnership=len(partnership),
        skipped=len(skipped),
        errors=len(errors),
    )

    return {
        "strategy_call_analyses": strategy,
        "sales_training_analyses": training,
        "leadership_analyses": leadership,
        "team_meeting_analyses": team,
        "client_review_analyses": client_review,
        "partnership_analyses": partnership,
        "skipped_calls": skipped,
        "errors": errors,
    }
