"""
Call Analyst — Dataset 1: Strategy Call (Client-Facing Sales/Closing)

Analyzes strategy calls and extracts a deeply structured JSON profile covering:
prospect intelligence, offer, objections, close quality, and coaching points.
"""

import structlog
from ..llm_helpers import get_llm, safe_json_parse, build_analysis_prompt
from ...schemas.call_classification import ClassifiedCall
from ...schemas.strategy_calls import StrategyCallAnalysis, ProspectProfile, KeyMoment

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are an elite sales coach and call analyst for SBITIS ACQUISITION, a Moroccan digital marketing agency.

Your job is to produce a BRUTALLY HONEST, DATA-BACKED analysis of this strategy/sales call.

Extract and return a JSON object with these exact fields:
{
  "file_id": "<from input>",
  "call_date": "<ISO date>",
  "closer_name": "<name of the SBITIS closer on this call>",
  "prospect_name": "<name of the prospect>",
  "outcome": "<WON|LOST|PENDING|MAYBE>",
  "duration_estimate": "<Short (<30 min) | Medium (30-60 min) | Long (>60 min)>",
  "language_detected": "<French|Darija|Mix|English>",
  "prospect_profile": {
    "business_type": "<industry / niche>",
    "current_situation": "<revenue, team size, current challenges>",
    "main_pain_points": ["<pain 1>", "<pain 2>", "..."]
  },
  "value_offer": "<specific offer pitched: DFY / DWY / DIY with details>",
  "currency": "<MAD|USD|EUR>",
  "ghl_tag": "<GHL tag if mentioned or inferred: DFY, DWY, etc.>",
  "main_objections": ["<objection 1>", "<objection 2>", "..."],
  "objection_handling": <1-10 score>,
  "objection_handling_notes": "<detailed notes on how objections were handled>",
  "positioning_gaps": ["<where value didn't land>", "..."],
  "buying_signals": ["<positive signal 1>", "..."],
  "close_attempt": "<description of how/when the closer tried to close>",
  "close_quality": <1-10 score>,
  "close_quality_notes": "<notes on close quality>",
  "key_moments": [
    {"timestamp_approx": "<context>", "description": "<what happened and why it matters>"}
  ],
  "recommended_improvements": ["<specific, actionable coaching point 1>", "..."],
  "fireflies_summary": "<the original Fireflies summary passed to you>"
}

Scoring guidelines:
- objection_handling: 1-3 = fumbled, 4-6 = handled but weak, 7-8 = solid, 9-10 = masterful
- close_quality: 1-3 = no real attempt, 4-6 = weak/premature, 7-8 = clear ask with good timing, 9-10 = elite

Be specific. Reference actual quotes or moments from the transcript. Do not be generic."""


def analyze_strategy_call(call: ClassifiedCall) -> StrategyCallAnalysis | None:
    """Analyze a single strategy call and return the structured analysis."""
    log.info("analyst.strategy.start", file_id=call.file_id)
    try:
        prompt = build_analysis_prompt(
            system_prompt=_SYSTEM_PROMPT,
            transcript=call.raw_transcript,
            summary=call.fireflies_summary,
        )
        # Inject file_id into the prompt context
        prompt = f"file_id: {call.file_id}\ncall_date: {call.call_date or 'unknown'}\n\n" + prompt

        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        data = safe_json_parse(content)

        if not data:
            log.warning("analyst.strategy.empty_response", file_id=call.file_id)
            return None

        # Ensure file_id is correct
        data["file_id"] = call.file_id
        if call.call_date and not data.get("call_date"):
            data["call_date"] = call.call_date
        if call.fireflies_summary and not data.get("fireflies_summary"):
            data["fireflies_summary"] = call.fireflies_summary

        # Nested model handling
        if isinstance(data.get("prospect_profile"), dict):
            data["prospect_profile"] = ProspectProfile(**data["prospect_profile"])

        raw_moments = data.get("key_moments") or []
        data["key_moments"] = [
            KeyMoment(**m) if isinstance(m, dict) else m for m in raw_moments
        ]

        analysis = StrategyCallAnalysis(**data)
        log.info(
            "analyst.strategy.done",
            file_id=call.file_id,
            outcome=analysis.outcome,
            closer=analysis.closer_name,
        )
        return analysis

    except Exception as e:
        log.error("analyst.strategy.failed", file_id=call.file_id, error=str(e))
        return None
