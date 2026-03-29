"""
Call Analyst — Dataset 6: Partnership Meeting
"""

import structlog
from ..llm_helpers import get_llm, safe_json_parse, build_analysis_prompt
from ...schemas.call_classification import ClassifiedCall
from ...schemas.partnership import PartnershipMeetingAnalysis, PartnershipOpportunity

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are analyzing a partnership or collaboration meeting for SBITIS ACQUISITION.

Extract a JSON object with these exact fields:
{
  "meeting_id": "<file_id>",
  "meeting_date": "<ISO date>",
  "meeting_type": "<partnership_exploration|jv_discussion|referral_agreement|agency_collab>",
  "partner_name": "<external partner name>",
  "partner_description": "<what they do, strengths, audience>",
  "sbitis_rep": "<SBITIS person on the call, usually Hamza>",
  "purpose_of_meeting": "<stated reason for this meeting>",
  "opportunities_identified": [
    {
      "type": "<referral|white_label|JV|collaboration|affiliate>",
      "description": "<what it entails>",
      "potential_value": "<estimated revenue or strategic value>",
      "next_step": "<concrete next step>",
      "owner": "<who from SBITIS handles this>"
    }
  ],
  "alignment_areas": ["<shared interest or audience overlap 1>", "..."],
  "concerns_or_risks": ["<risk or misalignment 1>", "..."],
  "commitments_made": ["<explicit commitment 1>", "..."],
  "next_steps": ["<step with owner 1>", "..."],
  "content_angles": ["<marketing or content idea 1>", "..."],
  "deal_status": "<exploring|active_negotiation|agreed|on_hold|dead>",
  "fireflies_summary": "<original Fireflies summary>"
}"""


def analyze_partnership_meeting(call: ClassifiedCall) -> PartnershipMeetingAnalysis | None:
    log.info("analyst.partnership.start", file_id=call.file_id)
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

        data["opportunities_identified"] = [
            PartnershipOpportunity(**o) if isinstance(o, dict) else o
            for o in (data.get("opportunities_identified") or [])
        ]

        analysis = PartnershipMeetingAnalysis(**data)
        log.info("analyst.partnership.done", file_id=call.file_id, partner=analysis.partner_name)
        return analysis

    except Exception as e:
        log.error("analyst.partnership.failed", file_id=call.file_id, error=str(e))
        return None
