"""
Integration test: full pipeline run with all external APIs mocked.

Simulates a complete daily run:
  kb_ingestion → fireflies_reader → call_analysts → data_aggregator
  → langsmith_storage → strategist → content_intelligence
  → output_writer → content_writer

No network calls are made. All external dependencies are mocked with
realistic data from tests/mock_data.py.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from sbitis_platform.graph import build_graph, create_initial_state
from sbitis_platform.state import SBITISState
from sbitis_platform.schemas.call_classification import CallType, ClassifiedCall
from sbitis_platform.schemas.strategy_calls import StrategyCallAnalysis, ProspectProfile
from sbitis_platform.schemas.meta_ads import MetaAdsReport, CampaignRecord, OfferType, FunnelStage
from sbitis_platform.schemas.content_intelligence import (
    ContentIntelligenceReport, ContentIdea, PersonalBrandBrief,
    ContentPlatform, FunnelStage as ContentFunnelStage
)
from tests.mock_data import (
    MOCK_FIREFLIES_API_RESPONSE,
    MOCK_META_CAMPAIGN_INSIGHTS,
    MOCK_CLOSER_METRICS,
    MOCK_FUNNEL_METRICS,
    MOCK_GHL_PIPELINE,
    MOCK_STRATEGY_ANALYSIS_JSON,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_strategy_analysis():
    data = {**MOCK_STRATEGY_ANALYSIS_JSON}
    data["prospect_profile"] = ProspectProfile(**data["prospect_profile"])
    return StrategyCallAnalysis(**data)


@pytest.fixture
def mock_classified_strategy_call():
    return ClassifiedCall(
        file_id="test-strategy-001",
        title="Strategy Call - Youssef Benali",
        call_type=CallType.STRATEGY_CALL,
        classification_confidence=0.90,
        raw_transcript="Hamza: Bonjour Youssef... Youssef: Ça va...",
        fireflies_summary="Sales call about DFY offer, 3500 MAD/month.",
        participants=["Hamza SBITI", "Youssef Benali"],
        call_date="2026-03-29",
        sentence_count=16,
    )


@pytest.fixture
def mock_meta_report():
    campaigns = [
        CampaignRecord(
            campaign_id=r["campaign_id"],
            campaign_name=r["campaign_name"],
            offer_type=OfferType.DFY,
            funnel_stage=FunnelStage.LEAD_GEN,
            spend=float(r["spend"]),
            impressions=int(r["impressions"]),
            clicks=int(r["clicks"]),
            ctr=float(r["ctr"]),
            leads=sum(int(a["value"]) for a in r.get("actions", []) if a.get("action_type") == "lead"),
            cpl=0.0,
            date_start="2026-03-22",
            date_end="2026-03-29",
        )
        for r in MOCK_META_CAMPAIGN_INSIGHTS
    ]
    return MetaAdsReport(
        period_start="2026-03-22",
        period_end="2026-03-29",
        campaigns=campaigns,
        total_spend=8950.0,
        total_impressions=330500,
        total_clicks=3330,
        total_leads=74,
        overall_ctr=1.01,
        overall_cpl=120.9,
        dfy_spend=6050.0,
        dfy_leads=56,
        dfy_cpl=108.0,
        dwy_spend=2100.0,
        dwy_leads=18,
        dwy_cpl=116.7,
    )


@pytest.fixture
def mock_content_report():
    return ContentIntelligenceReport(
        report_date="2026-03-29",
        dfy_funnel_bottleneck="Show rate at 67% — pre-frame content needed",
        top_objections_this_week=["C'est trop cher", "Je veux faire moi-même", "Mon associé doit valider"],
        content_ideas=[
            ContentIdea(
                rank=1,
                title="Comment j'ai aidé un artisan marocain à tripler ses ventes en 60 jours",
                hook="Tu dépenses des milliers de dirhams en pub et tu ne vois aucun résultat?",
                angle="Résultats prouvés > promesses vagues",
                platform=ContentPlatform.INSTAGRAM_REEL,
                funnel_stage=ContentFunnelStage.TOFU,
                format_notes="Reel 60s",
                data_source="Objection récurrente cette semaine",
            )
        ],
        whatsapp_tweaks=[],
        positioning_insights=[],
        personal_brand_brief=PersonalBrandBrief(
            weekly_theme="DFY results proof",
            positioning_statement="SBITIS DFY: résultats garantis ou on rembourse",
        ),
    )


# ── Graph compilation tests ───────────────────────────────────────────────────

class TestGraphCompilation:
    def test_graph_builds_without_error(self):
        app = build_graph()
        assert app is not None

    def test_initial_state_has_all_required_keys(self):
        state = create_initial_state()
        required_keys = [
            "run_id", "run_date", "errors",
            "raw_transcripts", "classified_calls",
            "strategy_call_analyses", "sales_training_analyses",
            "leadership_analyses", "team_meeting_analyses",
            "client_review_analyses", "partnership_analyses",
            "skipped_calls",
            "meta_ads_report", "closer_metrics", "funnel_metrics", "ghl_pipeline_summary",
            "langsmith_stored_ids",
            "strategic_report", "report_written",
            "content_intelligence_report", "content_written",
        ]
        for key in required_keys:
            assert key in state, f"Missing state key: {key}"

    def test_run_id_is_unique(self):
        s1 = create_initial_state()
        s2 = create_initial_state()
        assert s1["run_id"] != s2["run_id"]


# ── Node unit tests (with mocked dependencies) ────────────────────────────────

class TestFirefliesReaderNode:
    def test_classifies_strategy_call_correctly(self):
        """Fireflies reader correctly classifies a strategy call transcript."""
        from sbitis_platform.nodes.fireflies_reader import _heuristic_classify

        transcript = MOCK_FIREFLIES_API_RESPONSE["data"]["transcripts"][0]
        call_type, confidence = _heuristic_classify(transcript)
        assert call_type == CallType.STRATEGY_CALL

    def test_classifies_training_call_correctly(self):
        from sbitis_platform.nodes.fireflies_reader import _heuristic_classify

        transcript = MOCK_FIREFLIES_API_RESPONSE["data"]["transcripts"][1]
        call_type, confidence = _heuristic_classify(transcript)
        assert call_type == CallType.SALES_TRAINING

    def test_classifies_appointment_correctly(self):
        from sbitis_platform.nodes.fireflies_reader import _heuristic_classify

        transcript = MOCK_FIREFLIES_API_RESPONSE["data"]["transcripts"][2]
        call_type, confidence = _heuristic_classify(transcript)
        assert call_type == CallType.APPOINTMENT_SETTING


class TestMetaAdsClassification:
    def test_dfy_campaign_classified(self):
        from sbitis_platform.integrations.meta_ads import classify_campaign
        offer, funnel, client = classify_campaign("DFY - Lead Gen - Maroc - Lookalike")
        assert offer == OfferType.DFY
        assert client is None

    def test_dwy_campaign_classified(self):
        from sbitis_platform.integrations.meta_ads import classify_campaign
        offer, funnel, client = classify_campaign("DWY - Formation - Entrepreneurs")
        assert offer == OfferType.DWY

    def test_brand_awareness_classified(self):
        from sbitis_platform.integrations.meta_ads import classify_campaign
        offer, funnel, client = classify_campaign("Brand Awareness - Hamza SBITI")
        assert offer.value in ("BRAND_AWARENESS",)

    def test_retargeting_funnel_stage(self):
        from sbitis_platform.integrations.meta_ads import classify_campaign
        from sbitis_platform.schemas.meta_ads import FunnelStage
        offer, funnel, client = classify_campaign("DFY - Retargeting - Visiteurs site")
        assert funnel == FunnelStage.RETARGETING

    def test_client_campaign_with_known_client(self):
        from sbitis_platform.integrations.meta_ads import classify_campaign
        offer, funnel, client = classify_campaign("statix - leadgen campaign Q1")
        assert offer == OfferType.CLIENT_CAMPAIGN
        assert client == "Statix"


class TestStrategyAnalystOutput:
    def test_schema_validates_mock_llm_output(self, mock_strategy_analysis):
        """Mock LLM JSON output → StrategyCallAnalysis parses without error."""
        assert mock_strategy_analysis.file_id == "test-strategy-001"
        assert mock_strategy_analysis.outcome == "MAYBE"
        assert mock_strategy_analysis.objection_handling == 7
        assert mock_strategy_analysis.close_quality == 6
        assert len(mock_strategy_analysis.recommended_improvements) == 3

    def test_nested_models_resolved(self, mock_strategy_analysis):
        assert isinstance(mock_strategy_analysis.prospect_profile, ProspectProfile)
        assert mock_strategy_analysis.prospect_profile.business_type != ""


class TestDataAggregatorNode:
    def test_node_runs_with_mocked_data(self, mock_meta_report):
        """Data aggregator populates state correctly when client classes are mocked."""
        from sbitis_platform.nodes.data_aggregator import data_aggregator_node
        import sbitis_platform.nodes.data_aggregator as da_module

        state = create_initial_state()

        mock_meta_client = MagicMock()
        mock_meta_client.fetch_campaign_insights.return_value = mock_meta_report

        mock_sheets_client = MagicMock()
        mock_sheets_client.read_closer_metrics.return_value = MOCK_CLOSER_METRICS
        mock_sheets_client.read_funnel_metrics.return_value = MOCK_FUNNEL_METRICS

        mock_ghl_client = MagicMock()
        mock_ghl_client.get_pipeline_summary.return_value = MOCK_GHL_PIPELINE

        with patch.object(da_module, 'MetaAdsClient', return_value=mock_meta_client), \
             patch.object(da_module, 'GoogleSheetsClient', return_value=mock_sheets_client), \
             patch.object(da_module, 'GoHighLevelClient', return_value=mock_ghl_client):
            result = data_aggregator_node(state)

        assert result.get("meta_ads_report") is not None
        assert result.get("funnel_metrics") is not None
        assert result.get("ghl_pipeline_summary") is not None


class TestStrategistNodePromptBuilding:
    def test_format_context_includes_meta_data(self, mock_meta_report, mock_strategy_analysis):
        """_format_context builds a non-empty string with Meta Ads data."""
        import sbitis_platform.nodes.strategist as strat_module
        from sbitis_platform.nodes.strategist import _format_context

        state = create_initial_state()
        state["meta_ads_report"] = mock_meta_report
        state["strategy_call_analyses"] = [mock_strategy_analysis]
        state["funnel_metrics"] = MOCK_FUNNEL_METRICS
        state["closer_metrics"] = MOCK_CLOSER_METRICS

        mock_kb = MagicMock()
        mock_kb.get_agency_brain.return_value = "MOCKED AGENCY BRAIN"
        mock_kb.get_strategist_context.return_value = ""

        mock_ls = MagicMock()
        mock_ls.list_recent_strategy_calls.return_value = []

        with patch.object(strat_module, '_kb', mock_kb), \
             patch.object(strat_module, '_langsmith', mock_ls, create=True):
            context = _format_context(state)

        assert "MOCKED AGENCY BRAIN" in context
        assert "META ADS" in context
        assert "8,950" in context or "8950" in context  # total spend


class TestContentIntelligenceNode:
    def test_content_context_includes_brain(self, mock_strategy_analysis, mock_meta_report):
        """Content intelligence context includes agency brain."""
        from sbitis_platform.nodes.content_intelligence import _build_content_context

        state = create_initial_state()
        state["strategy_call_analyses"] = [mock_strategy_analysis]
        state["meta_ads_report"] = mock_meta_report
        state["funnel_metrics"] = MOCK_FUNNEL_METRICS

        with patch('sbitis_platform.nodes.content_intelligence._kb') as mock_kb:
            mock_kb.get_agency_brain.return_value = "MOCKED BRAIN CONTENT"
            mock_kb.get_content_strategy_context.return_value = ""
            context = _build_content_context(state)

        assert "MOCKED BRAIN CONTENT" in context


# ── DRY_RUN full pipeline test ────────────────────────────────────────────────

class TestDryRunPipeline:
    def test_graph_invokes_without_crashing_dry_run(
        self, mock_strategy_analysis, mock_meta_report, mock_content_report
    ):
        """
        Full pipeline smoke test — mocks every external call, confirms
        the graph runs to completion without exceptions.
        DRY_RUN=true so no writes happen.
        """
        import sbitis_platform.graph as graph_module

        mock_strategic_report = """## 1. EXECUTIVE SUMMARY
Test report — all systems operational.

## 2. FUNNEL BREAKDOWN
Leads: 74 → Booked: 28 → Showed: 19 → Closed: 5

## 7. THE ONE THING
**Fix Chakir's value-before-price sequence this week.**"""

        # Patch node functions at the graph module level so build_graph()
        # picks up mocked references when compiling the StateGraph.
        with \
            patch.object(graph_module, 'kb_ingestion_node', return_value={"errors": []}), \
            patch.object(graph_module, 'fireflies_reader_node', return_value={
                "classified_calls": [ClassifiedCall(
                    file_id="test-strategy-001",
                    title="Strategy Call - Youssef Benali",
                    call_type=CallType.STRATEGY_CALL,
                    classification_confidence=0.9,
                    raw_transcript="mock transcript",
                    sentence_count=16,
                )],
                "skipped_calls": [],
                "errors": [],
            }), \
            patch.object(graph_module, 'call_analysts_node', return_value={
                "strategy_call_analyses": [mock_strategy_analysis],
                "sales_training_analyses": [],
                "leadership_analyses": [],
                "team_meeting_analyses": [],
                "client_review_analyses": [],
                "partnership_analyses": [],
                "errors": [],
            }), \
            patch.object(graph_module, 'data_aggregator_node', return_value={
                "meta_ads_report": mock_meta_report,
                "closer_metrics": MOCK_CLOSER_METRICS,
                "funnel_metrics": MOCK_FUNNEL_METRICS,
                "ghl_pipeline_summary": MOCK_GHL_PIPELINE,
                "errors": [],
            }), \
            patch.object(graph_module, 'langsmith_storage_node', return_value={
                "langsmith_stored_ids": ["test-strategy-001"],
                "errors": [],
            }), \
            patch.object(graph_module, 'strategist_node', return_value={
                "strategic_report": mock_strategic_report,
                "errors": [],
            }), \
            patch.object(graph_module, 'content_intelligence_node', return_value={
                "content_intelligence_report": mock_content_report,
                "errors": [],
            }), \
            patch.object(graph_module, 'output_writer_node', return_value={
                "report_written": True,
                "report_sheet_url": "https://docs.google.com/spreadsheets/d/mock",
                "errors": [],
            }), \
            patch.object(graph_module, 'content_writer_node', return_value={
                "content_written": True,
                "errors": [],
            }):

            app = build_graph()
            initial_state = create_initial_state()
            final_state = app.invoke(initial_state)

        assert final_state is not None
        assert final_state.get("strategic_report") == mock_strategic_report
        assert final_state.get("report_written") is True
        assert final_state.get("content_written") is True
        assert final_state.get("content_intelligence_report") is not None
