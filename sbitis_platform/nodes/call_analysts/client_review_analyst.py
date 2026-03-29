"""
Call Analyst — Dataset 5: Client Coaching / Review

The goldmine for content angles, voice-of-customer language, and testimonials.
"""

import structlog
from ..llm_helpers import get_llm, safe_json_parse, build_analysis_prompt
from ...schemas.call_classification import ClassifiedCall
from ...schemas.client_review import ClientReviewAnalysis, ResultAchieved, ContentAngle
from ...knowledge_base.retriever import KnowledgeRetriever

log = structlog.get_logger(__name__)
_kb = KnowledgeRetriever()

_SYSTEM_PROMPT = """You are analyzing a client review or coaching session for SBITIS ACQUISITION.
These are goldmines for: content angles, voice-of-customer language, testimonials, and positioning insights.

Extract a JSON object with these exact fields:
{
  "session_id": "<file_id>",
  "session_date": "<ISO date>",
  "session_type": "<monthly_review|bi_weekly_review|coaching|onboarding|offboarding>",
  "client_name": "<client name>",
  "client_niche": "<client industry/niche>",
  "sbitis_account_manager": "<SBITIS person on the call>",
  "results_achieved": [
    {
      "metric": "<ROAS|leads|CPL|revenue|etc.>",
      "value": "<the number>",
      "period": "<time period>",
      "vs_target": "<above/below/on target>"
    }
  ],
  "client_wins": ["<positive transformation or result 1>", "..."],
  "client_challenges": ["<remaining friction 1>", "..."],
  "client_language_patterns": [
    "<exact phrase client used to describe their situation — use their words>"
  ],
  "content_angles": [
    {
      "angle": "<specific content angle or story>",
      "format_suggestion": "<reel|carousel|long-form|email|story>",
      "platform": "<Instagram|YouTube|WhatsApp|LinkedIn>",
      "funnel_stage": "<TOFU|MOFU|BOFU>",
      "rationale": "<why this would resonate — backed by client data or language>"
    }
  ],
  "testimonial_moments": [
    "<verbatim or near-verbatim quote usable as social proof>"
  ],
  "upsell_signals": ["<signal that client may be ready for expansion 1>", "..."],
  "action_points": ["<follow-up action 1>", "..."],
  "fireflies_summary": "<original Fireflies summary>"
}

For content_angles: be CREATIVE and SPECIFIC. Use the client's actual results and language.
For client_language_patterns: capture the EXACT words the client uses — this is gold for copywriting."""


def analyze_client_review(call: ClassifiedCall) -> ClientReviewAnalysis | None:
    log.info("analyst.client_review.start", file_id=call.file_id)
    try:
        kb_context = _kb.get_content_strategy_context()
        kb_block = f"\n\n{kb_context}\n\n" if kb_context else ""
        prompt = (
            f"session_id: {call.file_id}\nsession_date: {call.call_date or 'unknown'}\n\n"
            + kb_block
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

        data["results_achieved"] = [ResultAchieved(**r) if isinstance(r, dict) else r for r in (data.get("results_achieved") or [])]
        data["content_angles"] = [ContentAngle(**ca) if isinstance(ca, dict) else ca for ca in (data.get("content_angles") or [])]

        analysis = ClientReviewAnalysis(**data)
        log.info(
            "analyst.client_review.done",
            file_id=call.file_id,
            client=analysis.client_name,
            angles=len(analysis.content_angles),
        )
        return analysis

    except Exception as e:
        log.error("analyst.client_review.failed", file_id=call.file_id, error=str(e))
        return None
