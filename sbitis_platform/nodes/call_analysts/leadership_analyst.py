"""
Call Analyst — Dataset 3: Leadership / Board Meeting
"""

import structlog
from ..llm_helpers import get_llm, safe_json_parse, build_analysis_prompt
from ...schemas.call_classification import ClassifiedCall
from ...schemas.leadership import LeadershipMeetingAnalysis, IssueItem, GoalItem, DecisionMade

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are analyzing an internal SBITIS ACQUISITION leadership or board meeting.

Extract a JSON object with these exact fields:
{
  "meeting_id": "<file_id>",
  "meeting_date": "<ISO date>",
  "meeting_type": "<leadership|board|quarterly_review|planning_session>",
  "attendees": ["<name 1>", "..."],
  "executive_summary": "<2-3 sentences summarizing the session>",
  "goals_discussed": [
    {
      "goal": "<stated goal>",
      "timeframe": "<when to achieve>",
      "owner": "<who owns it>",
      "metric": "<how success is measured>"
    }
  ],
  "issues_raised": [
    {
      "category": "<sales|ops|hiring|product|finance|marketing>",
      "description": "<the issue>",
      "owner": "<who resolves it>"
    }
  ],
  "decisions_made": [
    {
      "decision": "<what was decided>",
      "rationale": "<why>",
      "impact": "<expected business impact>"
    }
  ],
  "next_steps": ["<step with owner 1>", "..."],
  "strategic_priorities": ["<priority 1>", "..."],
  "content_angles": ["<marketing/content idea 1>", "..."],
  "fireflies_summary": "<original Fireflies summary>"
}"""


def analyze_leadership_meeting(call: ClassifiedCall) -> LeadershipMeetingAnalysis | None:
    log.info("analyst.leadership.start", file_id=call.file_id)
    try:
        prompt = (
            f"meeting_id: {call.file_id}\nmeeting_date: {call.call_date or 'unknown'}\n\n"
            + build_analysis_prompt(_SYSTEM_PROMPT, call.raw_transcript, call.fireflies_summary)
        )
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        data = safe_json_parse(content)

        if not data:
            return None

        data["meeting_id"] = call.file_id
        if call.call_date and not data.get("meeting_date"):
            data["meeting_date"] = call.call_date
        if call.fireflies_summary and not data.get("fireflies_summary"):
            data["fireflies_summary"] = call.fireflies_summary

        data["goals_discussed"] = [GoalItem(**g) if isinstance(g, dict) else g for g in (data.get("goals_discussed") or [])]
        data["issues_raised"] = [IssueItem(**i) if isinstance(i, dict) else i for i in (data.get("issues_raised") or [])]
        data["decisions_made"] = [DecisionMade(**d) if isinstance(d, dict) else d for d in (data.get("decisions_made") or [])]

        analysis = LeadershipMeetingAnalysis(**data)
        log.info("analyst.leadership.done", file_id=call.file_id)
        return analysis

    except Exception as e:
        log.error("analyst.leadership.failed", file_id=call.file_id, error=str(e))
        return None
