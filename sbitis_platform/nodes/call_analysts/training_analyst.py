"""
Call Analyst — Dataset 2: Sales Training & Call Review
"""

import structlog
from ..llm_helpers import get_llm, safe_json_parse, build_analysis_prompt
from ...schemas.call_classification import ClassifiedCall
from ...schemas.sales_training import SalesTrainingAnalysis, CoachingPoint, ActionPoint

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are analyzing an internal SBITIS ACQUISITION sales training or call review session.

The trainer is usually Hamza SBITI. Closers are: Zineb Lahbabi, Chakir, Austin.

Extract a JSON object with these exact fields:
{
  "session_id": "<file_id>",
  "session_date": "<ISO date>",
  "session_type": "<call_review|training|roleplay|mixed>",
  "trainer": "<trainer name, usually Hamza>",
  "participants_closers": ["<closer 1>", "..."],
  "calls_reviewed": ["<call ID or description 1>", "..."],
  "key_remarks": ["<high-level insight 1>", "..."],
  "coaching_points": [
    {
      "closer": "<name>",
      "area": "<objection_handling|opener|close|tonality|framing|qualification|etc.>",
      "issue": "<specific problem identified>",
      "evidence": "<quote or moment from the session>",
      "recommendation": "<specific fix or drill>"
    }
  ],
  "action_points": [
    {
      "assignee": "<closer name>",
      "action": "<specific task>",
      "deadline": "<deadline or timeframe>"
    }
  ],
  "scripts_or_frameworks_shared": ["<script or technique 1>", "..."],
  "patterns_identified": ["<systemic issue pattern 1>", "..."],
  "fireflies_summary": "<original Fireflies summary>"
}

Be extremely specific. Quote exact phrases from the transcript as evidence."""


def analyze_sales_training(call: ClassifiedCall) -> SalesTrainingAnalysis | None:
    log.info("analyst.training.start", file_id=call.file_id)
    try:
        prompt = (
            f"session_id: {call.file_id}\nsession_date: {call.call_date or 'unknown'}\n\n"
            + build_analysis_prompt(_SYSTEM_PROMPT, call.raw_transcript, call.fireflies_summary)
        )
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        data = safe_json_parse(content)

        if not data:
            return None

        data["session_id"] = call.file_id
        if call.call_date and not data.get("session_date"):
            data["session_date"] = call.call_date
        if call.fireflies_summary and not data.get("fireflies_summary"):
            data["fireflies_summary"] = call.fireflies_summary

        data["coaching_points"] = [
            CoachingPoint(**cp) if isinstance(cp, dict) else cp
            for cp in (data.get("coaching_points") or [])
        ]
        data["action_points"] = [
            ActionPoint(**ap) if isinstance(ap, dict) else ap
            for ap in (data.get("action_points") or [])
        ]

        analysis = SalesTrainingAnalysis(**data)
        log.info("analyst.training.done", file_id=call.file_id, closer_count=len(analysis.participants_closers))
        return analysis

    except Exception as e:
        log.error("analyst.training.failed", file_id=call.file_id, error=str(e))
        return None
