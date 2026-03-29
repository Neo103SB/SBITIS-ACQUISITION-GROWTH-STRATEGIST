"""
Tests for all Pydantic schemas — validates that real LLM output can be
parsed and that field constraints are enforced correctly.
"""

import pytest
from pydantic import ValidationError
from tests.mock_data import MOCK_STRATEGY_ANALYSIS_JSON
from sbitis_platform.schemas.strategy_calls import StrategyCallAnalysis, ProspectProfile
from sbitis_platform.schemas.sales_training import SalesTrainingAnalysis
from sbitis_platform.schemas.leadership import LeadershipMeetingAnalysis
from sbitis_platform.schemas.team_meeting import TeamMeetingAnalysis
from sbitis_platform.schemas.client_review import ClientReviewAnalysis
from sbitis_platform.schemas.partnership import PartnershipMeetingAnalysis
from sbitis_platform.schemas.meta_ads import MetaAdsReport, CampaignRecord, OfferType, FunnelStage
from sbitis_platform.schemas.content_intelligence import (
    ContentIntelligenceReport, ContentIdea, WhatsAppMessageTweak,
    DFYPositioningInsight, PersonalBrandBrief, ContentPlatform, FunnelStage as ContentFunnelStage
)
from sbitis_platform.nodes.llm_helpers import safe_json_parse


# ── Dataset 1: Strategy Call ──────────────────────────────────────────────────

class TestStrategyCallSchema:
    def test_parses_full_mock_output(self):
        a = StrategyCallAnalysis(**MOCK_STRATEGY_ANALYSIS_JSON)
        assert a.file_id == "test-strategy-001"
        assert a.outcome == "MAYBE"
        assert a.currency == "MAD"
        assert a.objection_handling == 7
        assert a.close_quality == 6
        assert len(a.main_objections) == 2
        assert len(a.buying_signals) == 3

    def test_outcome_validation(self):
        data = {**MOCK_STRATEGY_ANALYSIS_JSON, "outcome": "INVALID"}
        with pytest.raises(ValidationError):
            StrategyCallAnalysis(**data)

    def test_currency_validation(self):
        data = {**MOCK_STRATEGY_ANALYSIS_JSON, "currency": "DH"}
        with pytest.raises(ValidationError):
            StrategyCallAnalysis(**data)

    def test_score_bounds(self):
        data = {**MOCK_STRATEGY_ANALYSIS_JSON, "objection_handling": 11}
        with pytest.raises(ValidationError):
            StrategyCallAnalysis(**data)

        data2 = {**MOCK_STRATEGY_ANALYSIS_JSON, "close_quality": 0}
        with pytest.raises(ValidationError):
            StrategyCallAnalysis(**data2)

    def test_nested_prospect_profile(self):
        a = StrategyCallAnalysis(**MOCK_STRATEGY_ANALYSIS_JSON)
        assert isinstance(a.prospect_profile, ProspectProfile)
        assert "E-commerce" in a.prospect_profile.business_type
        assert len(a.prospect_profile.main_pain_points) == 3

    def test_minimal_valid(self):
        """Only required fields — all optional fields should default cleanly."""
        a = StrategyCallAnalysis(file_id="min-001")
        assert a.outcome == "PENDING"
        assert a.currency == "MAD"
        assert a.objection_handling == 5
        assert a.main_objections == []


# ── Dataset 2: Sales Training ─────────────────────────────────────────────────

class TestSalesTrainingSchema:
    def test_valid_construction(self):
        a = SalesTrainingAnalysis(
            session_id="train-001",
            session_date="2026-03-29",
            trainer="Hamza SBITI",
            participants_closers=["Zineb Lahbabi", "Chakir"],
            session_type="call_review",
            coaching_points=[],
            action_points=[],
        )
        assert a.trainer == "Hamza SBITI"
        assert len(a.participants_closers) == 2

    def test_minimal_valid(self):
        a = SalesTrainingAnalysis(session_id="train-002")
        assert a.participants_closers == []
        assert a.coaching_points == []


# ── Dataset 3: Leadership ─────────────────────────────────────────────────────

class TestLeadershipSchema:
    def test_valid_construction(self):
        a = LeadershipMeetingAnalysis(
            meeting_id="lead-001",
            meeting_date="2026-03-29",
            attendees=["Hamza SBITI"],
            meeting_type="planning",
            strategic_priorities=["Scale DFY to 20 clients"],
            goals_discussed=[],
            decisions_made=[],
        )
        assert a.meeting_id == "lead-001"

    def test_minimal_valid(self):
        a = LeadershipMeetingAnalysis(meeting_id="lead-002")
        assert a.attendees == []


# ── Dataset 4: Team Meeting ───────────────────────────────────────────────────

class TestTeamMeetingSchema:
    def test_valid_construction(self):
        a = TeamMeetingAnalysis(
            meeting_id="team-001",
            team="Sales Team",
            attendees=["Zineb Lahbabi", "Chakir", "Austin"],
            client_issues=[],
            action_points=[],
        )
        assert a.team == "Sales Team"

    def test_minimal_valid(self):
        a = TeamMeetingAnalysis(meeting_id="team-002")
        assert a.action_points == []


# ── Dataset 5: Client Review ──────────────────────────────────────────────────

class TestClientReviewSchema:
    def test_valid_construction(self):
        a = ClientReviewAnalysis(
            session_id="review-001",
            client_name="Statix",
            session_date="2026-03-29",
            sbitis_account_manager="Hamza SBITI",
            results_achieved=[],
            content_angles=[],
            client_language_patterns=["Vous avez triplé nos leads en 2 mois!"],
            action_points=[],
        )
        assert a.client_name == "Statix"

    def test_minimal_valid(self):
        a = ClientReviewAnalysis(session_id="review-002")
        assert a.action_points == []


# ── Dataset 6: Partnership ────────────────────────────────────────────────────

class TestPartnershipSchema:
    def test_valid_construction(self):
        a = PartnershipMeetingAnalysis(
            meeting_id="partner-001",
            partner_name="Zakaria Agency",
            meeting_date="2026-03-29",
            meeting_type="referral",
            opportunities_identified=[],
            next_steps=[],
        )
        assert a.partner_name == "Zakaria Agency"

    def test_minimal_valid(self):
        a = PartnershipMeetingAnalysis(meeting_id="partner-002")
        assert a.next_steps == []


# ── Meta Ads schema ───────────────────────────────────────────────────────────

class TestMetaAdsSchema:
    def test_offer_type_enum(self):
        assert OfferType.DFY.value == "DFY"
        assert OfferType.DWY.value == "DWY"
        assert OfferType.BRAND_AWARENESS.value == "BRAND_AWARENESS"

    def test_campaign_record(self):
        c = CampaignRecord(
            campaign_id="120201234",
            campaign_name="DFY - Lead Gen - Maroc",
            offer_type=OfferType.DFY,
            funnel_stage=FunnelStage.LEAD_GEN,
            spend=4250.0,
            impressions=98500,
            clicks=1240,
            ctr=1.26,
            leads=34,
            cpl=125.0,
            date_start="2026-03-22",
            date_end="2026-03-29",
        )
        assert c.offer_type == OfferType.DFY
        assert c.leads == 34

    def test_meta_ads_report_minimal(self):
        r = MetaAdsReport(
            period_start="2026-03-22",
            period_end="2026-03-29",
            campaigns=[],
        )
        assert r.total_spend == 0.0
        assert r.total_leads == 0


# ── Content Intelligence schema ───────────────────────────────────────────────

class TestContentIntelligenceSchema:
    def test_content_idea(self):
        idea = ContentIdea(
            rank=1,
            title="Comment j'ai aidé un artisan marocain à tripler ses ventes en 60 jours",
            hook="Tu dépenses des milliers de dirhams en pub et tu ne vois aucun résultat?",
            angle="Résultats prouvés > promesses vagues",
            platform=ContentPlatform.INSTAGRAM_REEL,
            funnel_stage=ContentFunnelStage.TOFU,
            format_notes="Reel 60s",
            data_source="Objection récurrente: 'La pub ne marche pas pour moi'",
        )
        assert idea.rank == 1
        assert idea.platform == ContentPlatform.INSTAGRAM_REEL

    def test_whatsapp_tweak(self):
        tweak = WhatsAppMessageTweak(
            sequence_position="Message 1 — Day 0",
            current_issue="Message trop générique, faible taux de réponse",
            suggested_rewrite="Bonjour [Prénom], j'ai vu que tu gères ta pub toi-même. J'ai quelque chose qui peut t'intéresser — 5 minutes?",
            rationale="Personnalisation + pain point direct + micro-engagement au lieu de demande ouverte.",
        )
        assert tweak.suggested_rewrite is not None

    def test_full_report_construction(self):
        report = ContentIntelligenceReport(
            report_date="2026-03-29",
            dfy_funnel_bottleneck="Show rate at 67% — leads not showing up for calls",
            top_objections_this_week=["C'est trop cher", "Je veux faire moi-même"],
            content_ideas=[],
            whatsapp_tweaks=[],
            positioning_insights=[],
            personal_brand_brief=PersonalBrandBrief(
                this_week_angle="Hamza reveals the #1 mistake Moroccan businesses make with ads",
                recommended_format="Reel 45s",
                hook="J'ai analysé 100 comptes pub marocains...",
                storyline="Data-driven reveal of common mistakes → SBITIS solution",
                why_now="High volume of 'ads don't work' objection this week",
            ),
        )
        assert report.dfy_funnel_bottleneck != ""


# ── LLM helper: safe_json_parse ───────────────────────────────────────────────

class TestSafeJsonParse:
    def test_clean_json(self):
        result = safe_json_parse('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}

    def test_markdown_fenced_json(self):
        raw = '```json\n{"key": "value"}\n```'
        result = safe_json_parse(raw)
        assert result == {"key": "value"}

    def test_markdown_fence_no_lang(self):
        raw = '```\n{"key": "value"}\n```'
        result = safe_json_parse(raw)
        assert result == {"key": "value"}

    def test_trailing_comma(self):
        raw = '{"key": "value", "list": [1, 2, 3,]}'
        result = safe_json_parse(raw)
        assert result is not None
        assert result["list"] == [1, 2, 3]

    def test_invalid_json_returns_none(self):
        result = safe_json_parse("this is not json at all")
        assert result is None

    def test_empty_string(self):
        result = safe_json_parse("")
        assert result is None

    def test_json_embedded_in_text(self):
        raw = 'Here is the analysis:\n{"file_id": "001", "outcome": "WON"}\nEnd.'
        result = safe_json_parse(raw)
        assert result is not None
        assert result["outcome"] == "WON"
