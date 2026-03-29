"""
SBITIS Growth Intelligence Platform — LangGraph Workflow

Graph structure:
  START
    → kb_ingestion              (sync Drive SOPs/frameworks → ChromaDB — optional)
    → fireflies_reader          (fetch + classify transcripts)
    → call_analysts             (analyze each call by type)  ┐ fan-out
    → data_aggregator           (Meta Ads + Sheets + GHL)    ┘ concurrent
    → langsmith_storage         (persist analyses to datasets)
    → strategist                (generate CEO intelligence report)
    → output_writer             (write to Google Sheets)
  END
"""

import uuid
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from .state import SBITISState
from .nodes.kb_ingestion import kb_ingestion_node
from .nodes.fireflies_reader import fireflies_reader_node
from .nodes.call_analysts import call_analysts_node
from .nodes.data_aggregator import data_aggregator_node
from .nodes.langsmith_storage import langsmith_storage_node
from .nodes.strategist import strategist_node
from .nodes.output_writer import output_writer_node


def build_graph() -> StateGraph:
    """Construct and compile the SBITIS LangGraph pipeline."""

    builder = StateGraph(SBITISState)

    # ── Add nodes ─────────────────────────────────────────────────────────────
    builder.add_node("kb_ingestion", kb_ingestion_node)
    builder.add_node("fireflies_reader", fireflies_reader_node)
    builder.add_node("call_analysts", call_analysts_node)
    builder.add_node("data_aggregator", data_aggregator_node)
    builder.add_node("langsmith_storage", langsmith_storage_node)
    builder.add_node("strategist", strategist_node)
    builder.add_node("output_writer", output_writer_node)

    # ── Define edges ──────────────────────────────────────────────────────────
    # KB ingestion runs first (skips gracefully if not configured)
    builder.set_entry_point("kb_ingestion")
    builder.add_edge("kb_ingestion", "fireflies_reader")

    # After reading transcripts: fan-out to call analysts AND data aggregator
    builder.add_edge("fireflies_reader", "call_analysts")
    builder.add_edge("fireflies_reader", "data_aggregator")

    # Both branches must complete before storage
    builder.add_edge("call_analysts", "langsmith_storage")
    builder.add_edge("data_aggregator", "langsmith_storage")

    # After storage → generate strategic report
    builder.add_edge("langsmith_storage", "strategist")

    # After strategy → write output
    builder.add_edge("strategist", "output_writer")

    builder.add_edge("output_writer", END)

    return builder.compile()


def create_initial_state(run_date: str | None = None) -> SBITISState:
    """Create a fresh initial state for a pipeline run."""
    return SBITISState(
        run_id=str(uuid.uuid4()),
        run_date=run_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        errors=[],
        raw_transcripts=[],
        classified_calls=[],
        strategy_call_analyses=[],
        sales_training_analyses=[],
        leadership_analyses=[],
        team_meeting_analyses=[],
        client_review_analyses=[],
        partnership_analyses=[],
        skipped_calls=[],
        meta_ads_report=None,
        closer_metrics=[],
        funnel_metrics=None,
        ghl_pipeline_summary={},
        langsmith_stored_ids=[],
        strategic_report="",
        report_written=False,
        report_sheet_url="",
    )


# Compiled graph (singleton — import this in main.py)
graph = build_graph()
