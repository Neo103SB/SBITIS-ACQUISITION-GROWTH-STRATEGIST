"""
Tests for call classification logic.

Tests the heuristic classifier (title + sentence count) and verifies
that each of the 7 call types is correctly detected without any network calls.
"""

import pytest
from sbitis_platform.schemas.call_classification import CallType, ClassifiedCall
from sbitis_platform.nodes.fireflies_reader import _heuristic_classify


def _make_transcript(title: str, n_sentences: int, participants: list[str] | None = None) -> dict:
    """Build a minimal mock Fireflies transcript dict matching the actual API structure."""
    return {
        "title": title,
        # Sentences at top level (how Fireflies GraphQL returns them)
        "sentences": [{"text": f"Sentence {i}.", "speaker_name": "Speaker"} for i in range(n_sentences)],
        # meeting_attendees with displayName (how participants are returned)
        "meeting_attendees": [{"displayName": p} for p in (participants or [])],
    }


# ── Heuristic classifier tests ────────────────────────────────────────────────

class TestHeuristicClassifier:

    def test_appointment_setting_by_sentence_count(self):
        t = _make_transcript("Call with Ahmed", n_sentences=8)
        result, conf = _heuristic_classify(t)
        assert result == CallType.APPOINTMENT_SETTING
        assert conf >= 0.9

    def test_appointment_by_confirmation_title(self):
        t = _make_transcript("Confirmation appel Rachid", n_sentences=50)
        result, conf = _heuristic_classify(t)
        assert result == CallType.APPOINTMENT_SETTING

    def test_strategy_call_title(self):
        t = _make_transcript("Strategy Call - Youssef Benali", n_sentences=80)
        result, conf = _heuristic_classify(t)
        assert result == CallType.STRATEGY_CALL
        assert conf >= 0.85

    def test_strategy_call_by_closing_keyword(self):
        t = _make_transcript("Closing call Mohamed Faris", n_sentences=60)
        result, conf = _heuristic_classify(t)
        assert result == CallType.STRATEGY_CALL

    def test_sales_training_keywords(self):
        t = _make_transcript("Sales Training Session - Weekly Review", n_sentences=120)
        result, conf = _heuristic_classify(t)
        assert result == CallType.SALES_TRAINING

    def test_coaching_keyword(self):
        t = _make_transcript("Coaching call closers review", n_sentences=90)
        result, conf = _heuristic_classify(t)
        assert result == CallType.SALES_TRAINING

    def test_leadership_meeting(self):
        t = _make_transcript("Leadership Weekly Sync Q2", n_sentences=100)
        result, conf = _heuristic_classify(t)
        assert result == CallType.LEADERSHIP_MEETING

    def test_team_meeting(self):
        t = _make_transcript("Team Meeting Operations Update", n_sentences=80)
        result, conf = _heuristic_classify(t)
        assert result == CallType.TEAM_MEETING

    def test_client_review(self):
        t = _make_transcript("Client Review Monthly - Statix", n_sentences=70)
        result, conf = _heuristic_classify(t)
        assert result == CallType.CLIENT_REVIEW

    def test_partnership_call(self):
        t = _make_transcript("Partnership Discussion - Agency Collab", n_sentences=60)
        result, conf = _heuristic_classify(t)
        assert result == CallType.PARTNERSHIP_MEETING

    def test_all_internal_long_call_is_leadership(self):
        """All-internal participants + long call → LEADERSHIP_MEETING."""
        t = _make_transcript(
            "Weekly sync",
            n_sentences=90,
            participants=["Hamza SBITI", "Zineb Lahbabi"],
        )
        result, conf = _heuristic_classify(t)
        assert result == CallType.LEADERSHIP_MEETING

    def test_all_internal_short_call_is_team(self):
        """All-internal participants + short call → TEAM_MEETING."""
        t = _make_transcript(
            "Quick sync",
            n_sentences=40,
            participants=["Hamza SBITI", "Zineb Lahbabi"],
        )
        result, conf = _heuristic_classify(t)
        assert result == CallType.TEAM_MEETING

    def test_ambiguous_title_falls_to_llm(self):
        """Generic title + medium length → no confident heuristic result."""
        t = _make_transcript("Meeting with Ahmed", n_sentences=40)
        result, conf = _heuristic_classify(t)
        # Either returns None (needs LLM) or low confidence
        assert result is None or conf < 0.70

    def test_french_strategy_keyword(self):
        t = _make_transcript("Appel stratégie Nadia Kettani", n_sentences=75)
        result, conf = _heuristic_classify(t)
        assert result == CallType.STRATEGY_CALL

    def test_zero_sentence_count_skips_appointment(self):
        """Zero sentences → don't classify as appointment (avoid false positives)."""
        t = _make_transcript("Strategy Call Ahmed", n_sentences=0)
        result, conf = _heuristic_classify(t)
        # Title keyword should still classify correctly
        assert result == CallType.STRATEGY_CALL


# ── CallType enum tests ───────────────────────────────────────────────────────

class TestCallTypeEnum:
    def test_all_7_types_plus_unknown_exist(self):
        # Values are lowercase in the enum
        expected = {
            "strategy_call", "sales_training", "leadership_meeting",
            "team_meeting", "client_review", "partnership_meeting",
            "appointment_setting", "unknown",
        }
        actual = {ct.value for ct in CallType}
        assert expected == actual


# ── ClassifiedCall model tests ────────────────────────────────────────────────

class TestClassifiedCall:
    def test_full_construction(self):
        call = ClassifiedCall(
            file_id="test-001",
            title="Strategy Call - Ahmed",
            call_type=CallType.STRATEGY_CALL,
            classification_confidence=0.92,
            raw_transcript="Bonjour Ahmed...",
            fireflies_summary="Sales call with Ahmed about DFY offer.",
            participants=["Hamza SBITI", "Ahmed Benali"],
            call_date="2026-03-29",
            sentence_count=85,
        )
        assert call.file_id == "test-001"
        assert call.call_type == CallType.STRATEGY_CALL
        assert call.classification_confidence == 0.92
        assert len(call.participants) == 2

    def test_defaults(self):
        call = ClassifiedCall(
            file_id="test-002",
            title="Unknown",
            call_type=CallType.UNKNOWN,
            classification_confidence=0.3,
        )
        assert call.raw_transcript == ""
        assert call.participants == []
        assert call.sentence_count == 0
        assert call.fireflies_summary == ""
