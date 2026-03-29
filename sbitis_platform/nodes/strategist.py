"""
Node 5 — The Strategist (CEO / Chief Growth Officer Intelligence Node)

Takes ALL aggregated data and generates a brutal, data-backed strategic report.
This is the core intelligence output of the entire platform.
"""

import json
import structlog
from datetime import datetime

from ..state import SBITISState
from ..config import config
from ..integrations.langsmith_client import LangSmithStorage
from ..knowledge_base.retriever import KnowledgeRetriever
from .llm_helpers import get_llm

_kb = KnowledgeRetriever()

log = structlog.get_logger(__name__)

# ── Strategist system prompt ──────────────────────────────────────────────────

_STRATEGIST_SYSTEM = """You are the Chief Growth Strategist and fractional CEO for SBITIS ACQUISITION, a Moroccan digital marketing agency.

Your mandate: Generate a BRUTAL, DATA-BACKED strategic intelligence report. No fluff. No corporate speak. Pure signal.

You have access to:
1. Live Meta Ads performance data (overall + DFY/DWY breakdown)
2. Sales funnel metrics (Leads → Booked → Showed → Closed)
3. Closer-by-closer performance from the WAR Sheet
4. GoHighLevel CRM pipeline summary
5. Recent strategy call analyses (what's actually happening on calls)
6. Recent sales training session analyses

Your report MUST include all 7 sections below. Be specific, cite numbers, name names.

---

## REPORT STRUCTURE

### 1. EXECUTIVE SUMMARY
3-4 sentences. Current situation in plain language. What's working, what's on fire, what needs immediate attention.

### 2. FUNNEL BREAKDOWN
Analyze the full funnel: Lead Gen → Booked → Showed → Closed
- Show the exact conversion rates at each stage
- Identify the #1 bottleneck (where leads are dying)
- Compare to industry benchmarks where relevant
- Call out the DFY vs DWY split if data is available

### 3. CLOSER-BY-CLOSER ANALYSIS
For EACH closer with data:
- Overall performance rating (A/B/C/D)
- What they're doing WELL (with evidence from call analyses)
- Their primary weakness (cite specific call patterns)
- ONE concrete coaching action this week (specific, actionable)

### 4. CROSS-CALL PATTERNS (from recent analyses)
- Top 3 recurring objections across all calls
- Top 3 positioning gaps (where the offer isn't landing)
- Top 3 winning patterns (what's closing deals)
- Language patterns worth incorporating into scripts

### 5. ROOT CAUSE ANALYSIS
Pick the primary growth problem. Go 3 levels deep:
- Surface: What you see
- Intermediate: Why that's happening
- Root: The actual underlying cause
Format: Surface → Why? → Why? → Why? (root cause)

### 6. ACTION ITEMS
Laser-focused actions by channel. Format:
[PRIORITY: CRITICAL/HIGH/MEDIUM] [Channel]: [Action] → [Why/Evidence] → [Metric to track]

Channels: Sales Process | Meta Ads | Content/Positioning | WhatsApp Follow-Up | CRM/GHL | Team/Ops

Minimum 6 action items across at least 3 channels.

### 7. THE ONE THING
The single most important action for THIS WEEK. One sentence. Bold it.

---

Be SPECIFIC. Reference actual numbers. If data is missing, flag it explicitly.
Write for someone who will read this in 5 minutes and needs to know EXACTLY what to do."""


def _format_context(state: SBITISState) -> str:
    """Build the context block fed to the Strategist LLM."""
    parts: list[str] = []
    run_date = state.get("run_date", datetime.utcnow().strftime("%Y-%m-%d"))

    # ── Agency Brain — always injected first ────────────────────────────────
    brain = _kb.get_agency_brain()
    if brain:
        parts.append(brain)
        parts.append("")

    parts.append(f"REPORT DATE: {run_date}")
    parts.append("=" * 60)

    # ── Meta Ads ────────────────────────────────────────────────────────────
    meta = state.get("meta_ads_report")
    if meta:
        parts.append("\n## META ADS PERFORMANCE")
        parts.append(f"Period: {meta.period_start} → {meta.period_end} ({meta.currency})")
        parts.append(f"Total Spend: {meta.total_spend:,.0f} {meta.currency}")
        parts.append(f"Total Impressions: {meta.total_impressions:,}")
        parts.append(f"Total Leads: {meta.total_leads}")
        parts.append(f"Overall CPL: {meta.overall_cpl:,.1f} {meta.currency}")
        parts.append(f"Overall CTR: {meta.overall_ctr:.2f}%")
        parts.append("")
        parts.append(f"DFY → Spend: {meta.dfy_spend:,.0f} | Leads: {meta.dfy_leads} | CPL: {meta.dfy_cpl:,.1f}")
        parts.append(f"DWY → Spend: {meta.dwy_spend:,.0f} | Leads: {meta.dwy_leads} | CPL: {meta.dwy_cpl:,.1f}")
        parts.append(f"Brand Awareness → Spend: {meta.brand_awareness_spend:,.0f} | Impressions: {meta.brand_awareness_impressions:,}")
        parts.append(f"Client Campaigns Spend: {meta.client_campaigns_spend:,.0f}")

        if meta.breakdown_by_offer:
            parts.append("\nOffer Breakdown:")
            for offer, d in meta.breakdown_by_offer.items():
                parts.append(f"  {offer}: Spend={d['spend']:,.0f} | Leads={d['leads']} | CPL={d['cpl']:,.1f}")

        # Top campaigns by spend
        top_campaigns = sorted(meta.campaigns, key=lambda c: c.spend, reverse=True)[:5]
        if top_campaigns:
            parts.append("\nTop 5 Campaigns by Spend:")
            for c in top_campaigns:
                parts.append(f"  [{c.offer_type.value}] {c.campaign_name}: {c.spend:,.0f} | {c.leads} leads | CPL {c.cpl:,.1f}")
    else:
        parts.append("\n## META ADS PERFORMANCE\n⚠️ Data unavailable")

    # ── Funnel Metrics ───────────────────────────────────────────────────────
    funnel = state.get("funnel_metrics")
    if funnel:
        parts.append("\n## SALES FUNNEL METRICS")
        parts.append(f"Leads Generated: {funnel['leads_generated']}")
        parts.append(f"Booked Meetings: {funnel['booked_meetings']}")
        parts.append(f"Showed Up: {funnel['showed_meetings']} (Show Rate: {funnel['show_rate']}%)")
        parts.append(f"Closed: {funnel['closed']} (Close Rate from Shows: {funnel['close_rate']}%)")
        parts.append(f"Cash Collected: {funnel['cash_collected']:,.0f} {funnel['currency']}")
    else:
        parts.append("\n## SALES FUNNEL METRICS\n⚠️ Data unavailable")

    # ── Closer Metrics ───────────────────────────────────────────────────────
    closer_metrics = state.get("closer_metrics") or []
    if closer_metrics:
        parts.append("\n## CLOSER PERFORMANCE (WAR SHEET)")
        for cm in closer_metrics:
            parts.append(
                f"  {cm['closer_name']}: {cm['calls_taken']} calls | "
                f"WON:{cm['won']} LOST:{cm['lost']} PENDING:{cm['pending']} | "
                f"Close Rate: {cm['close_rate']}% | Revenue: {cm['revenue_collected']:,.0f}"
            )
    else:
        parts.append("\n## CLOSER PERFORMANCE\n⚠️ Data unavailable")

    # ── GHL Pipeline ────────────────────────────────────────────────────────
    ghl = state.get("ghl_pipeline_summary") or {}
    if ghl and not ghl.get("error"):
        parts.append("\n## GHL PIPELINE SUMMARY")
        parts.append(f"Total Opportunities: {ghl.get('total_opportunities', 0)}")
        if ghl.get("by_stage"):
            parts.append("By Stage: " + " | ".join(f"{k}: {v}" for k, v in ghl["by_stage"].items()))
        if ghl.get("by_tag"):
            parts.append("By Tag: " + " | ".join(f"{k}: {v}" for k, v in list(ghl["by_tag"].items())[:8]))
        recent_won = ghl.get("recent_won") or []
        if recent_won:
            parts.append(f"Recent Wins ({len(recent_won)}): " + ", ".join(w["name"] for w in recent_won[:5]))
    else:
        parts.append("\n## GHL PIPELINE\n⚠️ Data unavailable")

    # ── Recent Strategy Call Analyses ────────────────────────────────────────
    strategy_analyses = state.get("strategy_call_analyses") or []

    # Also pull historical from LangSmith
    try:
        ls = LangSmithStorage()
        historical = ls.list_recent_strategy_calls(limit=15)
        all_analyses = strategy_analyses + [type("obj", (object,), d) for d in historical]
    except Exception:
        all_analyses = strategy_analyses

    if all_analyses:
        parts.append(f"\n## RECENT STRATEGY CALL ANALYSES ({len(all_analyses)} calls)")
        for a in all_analyses[:10]:
            try:
                if hasattr(a, "closer_name"):
                    parts.append(
                        f"  [{a.call_date}] {a.closer_name} | {a.prospect_name} | "
                        f"{a.outcome} | Objections: {', '.join(a.main_objections[:2])} | "
                        f"Close Score: {a.close_quality}/10"
                    )
                elif isinstance(a, dict):
                    parts.append(
                        f"  [{a.get('call_date', '?')}] {a.get('closer_name', '?')} | "
                        f"{a.get('outcome', '?')} | "
                        f"Objections: {', '.join((a.get('main_objections') or [])[:2])} | "
                        f"Close: {a.get('close_quality', '?')}/10"
                    )
            except Exception:
                pass
    else:
        parts.append("\n## STRATEGY CALL ANALYSES\n⚠️ No recent calls analyzed")

    # ── Recent Training Analyses ─────────────────────────────────────────────
    training_analyses = state.get("sales_training_analyses") or []
    if training_analyses:
        parts.append(f"\n## RECENT TRAINING SESSIONS ({len(training_analyses)})")
        for t in training_analyses[:3]:
            try:
                patterns = ", ".join(t.patterns_identified[:2]) if t.patterns_identified else "none"
                parts.append(f"  [{t.session_date}] {t.session_type} — Patterns: {patterns}")
            except Exception:
                pass

    # ── Knowledge Base Context ───────────────────────────────────────────────
    try:
        kb_context = _kb.get_strategist_context()
        if kb_context:
            parts.append(f"\n## KNOWLEDGE BASE (SOPs & FRAMEWORKS)\n{kb_context}")
    except Exception as e:
        log.warning("strategist.kb_context_failed", error=str(e))

    return "\n".join(parts)


def strategist_node(state: SBITISState) -> dict:
    """
    LangGraph node: Generates the strategic intelligence report.
    """
    log.info("node.strategist.start")
    errors: list[str] = []

    try:
        context = _format_context(state)
        full_prompt = f"{_STRATEGIST_SYSTEM}\n\n{'='*60}\nDATA CONTEXT:\n{'='*60}\n{context}"

        llm = get_llm()
        response = llm.invoke(full_prompt)
        report = response.content if hasattr(response, "content") else str(response)

        log.info("node.strategist.done", report_length=len(report))
        return {"strategic_report": report, "errors": errors}

    except Exception as e:
        msg = f"Strategist node failed: {e}"
        log.error("node.strategist.failed", error=str(e))
        fallback = f"# ⚠️ SBITIS INTELLIGENCE REPORT — {state.get('run_date', 'UNKNOWN DATE')}\n\nStrategist node failed to generate report.\n\nError: {e}\n\nPlease check logs."
        return {"strategic_report": fallback, "errors": [msg]}
