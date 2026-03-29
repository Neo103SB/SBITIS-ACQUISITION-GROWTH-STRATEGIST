"""
Node 4 — LangSmith Storage

Saves all newly analyzed calls into their respective LangSmith datasets.
Idempotent: running twice on the same data updates rather than duplicates.
"""

import structlog
from ..state import SBITISState
from ..integrations.langsmith_client import LangSmithStorage

log = structlog.get_logger(__name__)


def langsmith_storage_node(state: SBITISState) -> dict:
    """
    LangGraph node: Persists all call analyses to LangSmith datasets.
    Returns list of stored IDs.
    """
    log.info("node.langsmith_storage.start")
    storage = LangSmithStorage()
    stored_ids: list[str] = []
    errors: list[str] = []

    # ── Dataset 1: Strategy Calls ─────────────────────────────────────────────
    for analysis in state.get("strategy_call_analyses") or []:
        try:
            example_id = storage.save_strategy_call(analysis)
            stored_ids.append(example_id)
        except Exception as e:
            errors.append(f"LangSmith strategy call {analysis.file_id}: {e}")
            log.error("langsmith_storage.strategy_failed", id=analysis.file_id, error=str(e))

    # ── Dataset 2: Sales Training ─────────────────────────────────────────────
    for analysis in state.get("sales_training_analyses") or []:
        try:
            example_id = storage.save_sales_training(analysis)
            stored_ids.append(example_id)
        except Exception as e:
            errors.append(f"LangSmith training {analysis.session_id}: {e}")

    # ── Dataset 3: Leadership Meetings ────────────────────────────────────────
    for analysis in state.get("leadership_analyses") or []:
        try:
            example_id = storage.save_leadership_meeting(analysis)
            stored_ids.append(example_id)
        except Exception as e:
            errors.append(f"LangSmith leadership {analysis.meeting_id}: {e}")

    # ── Dataset 4: Team Meetings ──────────────────────────────────────────────
    for analysis in state.get("team_meeting_analyses") or []:
        try:
            example_id = storage.save_team_meeting(analysis)
            stored_ids.append(example_id)
        except Exception as e:
            errors.append(f"LangSmith team meeting {analysis.meeting_id}: {e}")

    # ── Dataset 5: Client Reviews ─────────────────────────────────────────────
    for analysis in state.get("client_review_analyses") or []:
        try:
            example_id = storage.save_client_review(analysis)
            stored_ids.append(example_id)
        except Exception as e:
            errors.append(f"LangSmith client review {analysis.session_id}: {e}")

    # ── Dataset 6: Partnership Meetings ───────────────────────────────────────
    for analysis in state.get("partnership_analyses") or []:
        try:
            example_id = storage.save_partnership_meeting(analysis)
            stored_ids.append(example_id)
        except Exception as e:
            errors.append(f"LangSmith partnership {analysis.meeting_id}: {e}")

    log.info(
        "node.langsmith_storage.done",
        stored=len(stored_ids),
        errors=len(errors),
    )

    return {
        "langsmith_stored_ids": stored_ids,
        "errors": errors,
    }
