"""LangGraph state definition for the SBITIS Growth Intelligence Platform."""

from typing import TypedDict, Optional, Annotated
import operator

from .schemas import (
    ClassifiedCall,
    StrategyCallAnalysis,
    SalesTrainingAnalysis,
    LeadershipMeetingAnalysis,
    TeamMeetingAnalysis,
    ClientReviewAnalysis,
    PartnershipMeetingAnalysis,
    MetaAdsReport,
)


class CloserMetrics(TypedDict):
    closer_name: str
    calls_taken: int
    won: int
    lost: int
    pending: int
    maybe: int
    close_rate: float  # won / (won + lost)
    revenue_collected: float


class FunnelMetrics(TypedDict):
    leads_generated: int
    booked_meetings: int
    showed_meetings: int
    show_rate: float
    closed: int
    close_rate: float
    cash_collected: float
    currency: str


class SBITISState(TypedDict):
    """
    Full shared state flowing through the LangGraph pipeline.
    Each node reads from this state and writes its outputs back into it.
    """

    # ── Run metadata ─────────────────────────────────────────────────────────
    run_id: str
    run_date: str  # ISO date "YYYY-MM-DD"
    errors: Annotated[list[str], operator.add]  # accumulates errors from all nodes

    # ── Node 1: Fireflies Reader outputs ─────────────────────────────────────
    raw_transcripts: list[dict]  # Raw Fireflies API responses
    classified_calls: list[ClassifiedCall]  # After classification

    # ── Node 2: Call Analyst outputs ─────────────────────────────────────────
    strategy_call_analyses: Annotated[list[StrategyCallAnalysis], operator.add]
    sales_training_analyses: Annotated[list[SalesTrainingAnalysis], operator.add]
    leadership_analyses: Annotated[list[LeadershipMeetingAnalysis], operator.add]
    team_meeting_analyses: Annotated[list[TeamMeetingAnalysis], operator.add]
    client_review_analyses: Annotated[list[ClientReviewAnalysis], operator.add]
    partnership_analyses: Annotated[list[PartnershipMeetingAnalysis], operator.add]
    skipped_calls: Annotated[list[str], operator.add]  # appointment setting etc.

    # ── Node 3: Data Aggregator outputs ──────────────────────────────────────
    meta_ads_report: Optional[MetaAdsReport]
    closer_metrics: list[CloserMetrics]
    funnel_metrics: Optional[FunnelMetrics]
    ghl_pipeline_summary: dict  # Raw GHL pipeline data

    # ── Node 4: LangSmith Storage ─────────────────────────────────────────────
    langsmith_stored_ids: Annotated[list[str], operator.add]  # IDs of saved records

    # ── Node 5: Strategist output ─────────────────────────────────────────────
    strategic_report: str  # Final markdown/text report

    # ── Node 6: Output Writer ─────────────────────────────────────────────────
    report_written: bool
    report_sheet_url: str
