"""
Call Analyst — Dataset 4: Team Meeting (Back/Middle Office)
"""

import structlog
from ..llm_helpers import get_llm, safe_json_parse, build_analysis_prompt
from ...schemas.call_classification import ClassifiedCall
from ...schemas.team_meeting import TeamMeetingAnalysis, ClientIssue, TeamActionPoint

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are analyzing an internal SBITIS ACQUISITION team meeting.
This covers back-office and middle-office teams: media buyers, content creators, video editors, operations.

Extract a JSON object with these exact fields:
{
  "meeting_id": "<file_id>",
  "meeting_date": "<ISO date>",
  "team": "<media_buying|content|video|ops|mixed>",
  "attendees": ["<name 1>", "..."],
  "executive_summary": "<2-3 sentence overview>",
  "client_issues": [
    {
      "client_name": "<name>",
      "issue": "<delivery or performance issue>",
      "severity": "<low|medium|high|critical>",
      "owner": "<who resolves it>",
      "resolution_plan": "<plan or next step>"
    }
  ],
  "operational_issues": ["<internal process issue 1>", "..."],
  "action_points": [
    {
      "assignee": "<name>",
      "department": "<media_buying|content|video|ops|all>",
      "action": "<specific task>",
      "deadline": "<deadline>",
      "priority": "<low|medium|high|urgent>"
    }
  ],
  "wins_celebrated": ["<win or milestone 1>", "..."],
  "content_angles": ["<content idea 1>", "..."],
  "fireflies_summary": "<original Fireflies summary>"
}"""


def analyze_team_meeting(call: ClassifiedCall) -> TeamMeetingAnalysis | None:
    log.info("analyst.team_meeting.start", file_id=call.file_id)
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

        data["client_issues"] = [ClientIssue(**ci) if isinstance(ci, dict) else ci for ci in (data.get("client_issues") or [])]
        data["action_points"] = [TeamActionPoint(**ap) if isinstance(ap, dict) else ap for ap in (data.get("action_points") or [])]

        analysis = TeamMeetingAnalysis(**data)
        log.info("analyst.team_meeting.done", file_id=call.file_id)
        return analysis

    except Exception as e:
        log.error("analyst.team_meeting.failed", file_id=call.file_id, error=str(e))
        return None
