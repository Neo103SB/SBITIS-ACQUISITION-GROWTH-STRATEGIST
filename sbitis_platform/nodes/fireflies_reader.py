"""
Node 1 — Fireflies Reader & Classifier

Fetches recent transcripts from Fireflies.ai and classifies each one
into one of 7 call types using a heuristic-first approach, with LLM fallback.
"""

import re
import json
import structlog
from datetime import datetime

from ..state import SBITISState
from ..config import config
from ..integrations.fireflies import FirefliesClient
from ..schemas.call_classification import CallType, ClassifiedCall
from .llm_helpers import get_llm, safe_json_parse

log = structlog.get_logger(__name__)

# ── Heuristic classification ──────────────────────────────────────────────────

# Known team member names (closers, trainers, internal)
INTERNAL_NAMES = {
    "hamza", "zineb", "chakir", "austin", "sbiti", "lahbabi",
    "zakaria", "media buyer", "content creator",
}

TITLE_PATTERNS: list[tuple[re.Pattern, CallType]] = [
    # Strategy / Sales call — client-facing
    (re.compile(r"\bstrategy\s+call\b|appel\s+strat[eé]g|closing\s+call|sales\s+call", re.I), CallType.STRATEGY_CALL),
    # Appointment setting
    (re.compile(r"\bappointment\b|\bappt\b|\bqualif\b|\bdiscovery\b|\bSDR\b|\bconfirmation\b|\bconfirm\s+appel\b", re.I), CallType.APPOINTMENT_SETTING),
    # Sales training / call review
    (re.compile(r"\btraining\b|\bcall\s+review\b|\bcoaching\b|\broleplay\b|\borientation\s+vente", re.I), CallType.SALES_TRAINING),
    # Leadership / board
    (re.compile(r"\bboard\b|\bleadership\b|\breunion\s+de\s+direction\b|\bplanning\s+session\b|\bQ[1-4]\b", re.I), CallType.LEADERSHIP_MEETING),
    # Partnership
    (re.compile(r"\bpartnership\b|\bpartenariat\b|\bcollab\b|\bJV\b|\baffili", re.I), CallType.PARTNERSHIP_MEETING),
    # Client review / coaching
    (re.compile(r"\bclient\s+(review|coaching|bilan|suivi|monthly|bi.weekly)\b|revue\s+client", re.I), CallType.CLIENT_REVIEW),
    # Team meeting
    (re.compile(r"\bteam\s+(meeting|standup|sync)\b|r[eé]union\s+[eé]quipe\b|back.office|middle.office", re.I), CallType.TEAM_MEETING),
]


def _heuristic_classify(transcript: dict) -> tuple[CallType | None, float]:
    """
    Returns (CallType, confidence) if heuristic is confident, else (None, 0.0).
    Uses title keywords + sentence count (reliable proxy when duration metadata is broken).
    """
    title = (transcript.get("title") or "").strip()
    sentence_count = FirefliesClient.get_sentence_count(transcript)
    participants = FirefliesClient.get_participants(transcript)
    participants_lower = {p.lower() for p in participants}

    # Short calls (< 20 sentences) are almost certainly appointment setting
    if sentence_count < 20 and sentence_count > 0:
        return CallType.APPOINTMENT_SETTING, 0.92

    # Title keyword matching
    for pattern, call_type in TITLE_PATTERNS:
        if pattern.search(title):
            return call_type, 0.90

    # Participant-based heuristics
    # If ALL participants are internal → internal meeting
    # Match by token so "Hamza SBITI" matches {"hamza", "sbiti"} in INTERNAL_NAMES
    def _is_internal(name: str) -> bool:
        return any(token in INTERNAL_NAMES for token in name.lower().split())

    external_participants = {p for p in participants_lower if not _is_internal(p)}
    all_internal = len(external_participants) == 0 and len(participants_lower) > 0

    if all_internal:
        # Long internal call with many sentences → likely leadership
        if sentence_count > 80:
            return CallType.LEADERSHIP_MEETING, 0.70
        # Shorter internal → team meeting
        return CallType.TEAM_MEETING, 0.65

    # Long calls with external participant and not classified above → likely strategy call
    if sentence_count > 50 and not all_internal:
        return CallType.STRATEGY_CALL, 0.65

    return None, 0.0  # needs LLM


_CLASSIFIER_PROMPT = """You are classifying a meeting transcript for SBITIS ACQUISITION, a Moroccan digital marketing agency.

Classify the following meeting into EXACTLY ONE of these 7 types:
1. strategy_call       — Client-facing sales/closing call (closer + prospect). Main pipeline.
2. appointment_setting — Short SDR calls (5-12 min) to qualify and book.
3. sales_training      — Internal coaching, roleplays, or Hamza reviewing calls with closers (Zineb, Chakir, Austin).
4. leadership_meeting  — Internal strategic planning, goals, board-level issues.
5. team_meeting        — Back/middle office: media buyers, content creators, video editors.
6. client_review       — Monthly/bi-weekly reviews with paying clients. Goldmine for content.
7. partnership_meeting — External meetings with agency owners or partners (e.g. Zakaria).

Meeting title: {title}
Participants: {participants}
Sentence count: {sentence_count}
First 300 words of transcript:
{excerpt}

Respond with ONLY a JSON object:
{{"call_type": "<one of the 7 types>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}"""


def _llm_classify(transcript: dict) -> tuple[CallType, float]:
    """Use LLM to classify when heuristic confidence is low."""
    title = transcript.get("title") or ""
    participants = FirefliesClient.get_participants(transcript)
    sentence_count = FirefliesClient.get_sentence_count(transcript)
    full_text = FirefliesClient.extract_full_text(transcript)
    excerpt = " ".join(full_text.split()[:300])

    prompt = _CLASSIFIER_PROMPT.format(
        title=title,
        participants=", ".join(participants),
        sentence_count=sentence_count,
        excerpt=excerpt,
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        parsed = safe_json_parse(content)
        raw_type = parsed.get("call_type", "unknown").lower().replace(" ", "_")
        confidence = float(parsed.get("confidence", 0.5))
        try:
            call_type = CallType(raw_type)
        except ValueError:
            call_type = CallType.UNKNOWN
        return call_type, confidence
    except Exception as e:
        log.error("classifier.llm_failed", error=str(e))
        return CallType.UNKNOWN, 0.0


# ── Main node function ────────────────────────────────────────────────────────

def fireflies_reader_node(state: SBITISState) -> dict:
    """
    LangGraph node: Fetches new Fireflies transcripts and classifies them.
    Updates: raw_transcripts, classified_calls, errors
    """
    log.info("node.fireflies_reader.start")
    errors: list[str] = []
    classified: list[ClassifiedCall] = []

    try:
        client = FirefliesClient()
        transcripts = client.get_recent_transcripts()
    except Exception as e:
        msg = f"Fireflies fetch failed: {e}"
        log.error("node.fireflies_reader.fetch_failed", error=str(e))
        return {"raw_transcripts": [], "classified_calls": [], "errors": [msg]}

    for t in transcripts:
        file_id = t.get("id", "unknown")
        try:
            # Heuristic classification
            call_type, confidence = _heuristic_classify(t)
            method = "heuristic"

            # Fall back to LLM if confidence is low
            if call_type is None or confidence < 0.70:
                call_type, confidence = _llm_classify(t)
                method = "llm"

            # Build full text and summary
            full_text = FirefliesClient.extract_full_text(t)
            summary = FirefliesClient.extract_summary(t)
            sentence_count = FirefliesClient.get_sentence_count(t)
            participants = FirefliesClient.get_participants(t)

            # Parse call date
            raw_date = t.get("date")
            call_date = None
            if raw_date:
                try:
                    # Fireflies returns epoch ms or ISO string
                    if isinstance(raw_date, (int, float)):
                        call_date = datetime.utcfromtimestamp(raw_date / 1000).strftime("%Y-%m-%d")
                    else:
                        call_date = str(raw_date)[:10]
                except Exception:
                    call_date = str(raw_date)

            classified_call = ClassifiedCall(
                file_id=file_id,
                title=t.get("title") or "",
                duration_seconds=t.get("duration"),
                sentence_count=sentence_count,
                call_type=call_type,
                classification_method=method,
                classification_confidence=confidence,
                raw_transcript=full_text,
                fireflies_summary=summary,
                call_date=call_date,
                participants=participants,
                skip_deep_analysis=(call_type == CallType.APPOINTMENT_SETTING),
            )
            classified.append(classified_call)
            log.info(
                "node.fireflies_reader.classified",
                id=file_id,
                call_type=call_type.value,
                method=method,
                confidence=round(confidence, 2),
            )

        except Exception as e:
            msg = f"Classification failed for transcript {file_id}: {e}"
            log.error("node.fireflies_reader.classify_failed", id=file_id, error=str(e))
            errors.append(msg)

    log.info(
        "node.fireflies_reader.done",
        total=len(transcripts),
        classified=len(classified),
        errors=len(errors),
    )

    return {
        "raw_transcripts": transcripts,
        "classified_calls": classified,
        "errors": errors,
    }
