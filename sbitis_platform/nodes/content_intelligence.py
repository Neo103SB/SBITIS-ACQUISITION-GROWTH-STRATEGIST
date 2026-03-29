"""
Node 7 — Content Intelligence (DFY Growth Engine)

The flywheel node. Takes all call intelligence, funnel data, and positioning
gaps — outputs a concrete weekly content strategy that feeds back into:
  • Lead quality (better pre-framing → higher show rate)
  • Close rate (content overcomes objections before the call)
  • Personal brand (Hamza's authority + trust content)
  • Meta Ads (new angles from actual prospect language)
  • WhatsApp sequences (data-backed copy improvements)

Focused 100% on DFY offer.
"""

import json
import structlog
from datetime import datetime

from ..state import SBITISState
from ..config import config
from ..schemas.content_intelligence import (
    ContentIntelligenceReport, ContentIdea, WhatsAppMessageTweak,
    DFYPositioningInsight, PersonalBrandBrief, ContentPlatform, FunnelStage
)
from ..knowledge_base.retriever import KnowledgeRetriever
from .llm_helpers import get_llm, safe_json_parse

log = structlog.get_logger(__name__)
_kb = KnowledgeRetriever()

# ── System prompt ─────────────────────────────────────────────────────────────

_CONTENT_INTELLIGENCE_PROMPT = """You are the Chief Content Strategist and Growth Architect for SBITIS ACQUISITION.

Your job: Turn raw sales intelligence into a concrete, data-backed weekly content strategy for the DFY (Done For You) offer.

CONTEXT ABOUT SBITIS:
- Owner: Hamza SBITI (personal brand — Instagram + YouTube)
- Primary offer: DFY digital marketing (agency does everything for the client)
- Market: Moroccan businesses (French/Darija-speaking), some international
- Goal: More qualified DFY leads → higher show rate → better close rate
- Closers: Zineb, Chakir, Austin (Hamza also closes)

THE FLYWHEEL YOU ARE OPTIMIZING:
Hamza's Content (TOFU) → Targeted Leads → WhatsApp Pre-framing → Qualified Calls → DFY Clients → Client Results → More Content

YOUR TASK:
Based on the sales intelligence below, generate a JSON content strategy with these exact fields.

The strategy must be:
1. SPECIFIC — reference actual objections, actual client wins, actual language from the data
2. ACTIONABLE — someone can execute the content idea immediately
3. CONNECTED — every piece of content should pre-frame, overcome an objection, or build trust for the DFY offer
4. PLATFORM-AWARE — different hooks and formats for Reel vs Carousel vs YouTube vs WhatsApp

Return ONLY valid JSON matching this schema:
{
  "report_date": "<ISO date>",
  "dfy_funnel_bottleneck": "<single sentence: where DFY leads are dying right now>",
  "top_objections_this_week": ["<objection 1>", "<objection 2>", "<objection 3>"],
  "top_buying_signals": ["<signal 1>", "<signal 2>", "<signal 3>"],
  "content_ideas": [
    {
      "rank": 1,
      "title": "<working title>",
      "hook": "<exact opening line — make it scroll-stopping>",
      "angle": "<the narrative angle — what story or frame are you using>",
      "platform": "<Instagram Reel | Instagram Carousel | Instagram Story | YouTube Short | YouTube Long-Form | WhatsApp | Email>",
      "funnel_stage": "<TOFU | MOFU | BOFU>",
      "format_notes": "<length, structure, CTA>",
      "data_source": "<what data insight drives this — be specific>",
      "objective": "<what this content achieves in the funnel>",
      "example_voc": "<voice-of-customer quote to use>"
    }
  ],
  "whatsapp_tweaks": [
    {
      "sequence_position": "<e.g. 'Message 1 — immediately after booking'>",
      "current_issue": "<what's likely failing>",
      "suggested_rewrite": "<the improved message — write the actual copy>",
      "rationale": "<why this will improve show rate>"
    }
  ],
  "positioning_insights": [
    {
      "gap": "<where DFY value isn't landing>",
      "root_cause": "<why>",
      "content_fix": "<content that pre-frames this>",
      "ad_angle": "<Meta ad angle that addresses this>",
      "whatsapp_fix": "<WhatsApp message that handles this pre-call>"
    }
  ],
  "personal_brand_brief": {
    "weekly_theme": "<overarching theme for Hamza's content this week>",
    "authority_post": {
      "rank": 1,
      "title": "<title>",
      "hook": "<hook>",
      "angle": "<angle>",
      "platform": "<YouTube Long-Form | Instagram Carousel>",
      "funnel_stage": "TOFU",
      "format_notes": "<>",
      "data_source": "<>",
      "objective": "establish authority",
      "example_voc": "<>"
    },
    "engagement_post": { ... same structure ... },
    "trust_post": { ... same structure ... },
    "positioning_statement": "<how to position Hamza vs the market this week — 1-2 sentences>",
    "content_to_avoid": ["<topic to avoid 1>"]
  },
  "meta_ad_angles": [
    "<specific new ad angle to test — write the actual hook/first line>"
  ],
  "content_priority_this_week": "<THE ONE content priority — single sentence>"
}

Generate 5-7 content ideas. Make the WhatsApp rewrites actually usable copy.
Every insight must be grounded in the data provided — no generic advice."""


def _build_content_context(state: SBITISState) -> str:
    """Compile all relevant intelligence for the content strategist."""
    parts: list[str] = []
    run_date = state.get("run_date", datetime.utcnow().strftime("%Y-%m-%d"))
    parts.append(f"REPORT DATE: {run_date}")

    # ── Funnel data ───────────────────────────────────────────────────────────
    funnel = state.get("funnel_metrics")
    if funnel:
        parts.append("\n## FUNNEL METRICS (DFY Focus)")
        parts.append(f"Leads → {funnel['leads_generated']} | Booked → {funnel['booked_meetings']} | "
                     f"Showed → {funnel['showed_meetings']} ({funnel['show_rate']}%) | "
                     f"Closed → {funnel['closed']} ({funnel['close_rate']}%)")
        parts.append(f"Cash Collected: {funnel['cash_collected']:,.0f} {funnel['currency']}")

        # Identify bottleneck for content signal
        if funnel["leads_generated"] > 0:
            book_rate = funnel["booked_meetings"] / funnel["leads_generated"] * 100 if funnel["leads_generated"] else 0
            if book_rate < 30:
                parts.append("⚠️ BOTTLENECK: Lead → Booking conversion is low — content needs to pre-qualify better")
            elif funnel["show_rate"] < 60:
                parts.append("⚠️ BOTTLENECK: High no-show rate — WhatsApp pre-framing needs work")
            elif funnel["close_rate"] < 25:
                parts.append("⚠️ BOTTLENECK: Low close rate from shows — pre-framing content or closer skills")

    # ── Strategy call objections & patterns ───────────────────────────────────
    strategy_analyses = state.get("strategy_call_analyses") or []
    if strategy_analyses:
        parts.append(f"\n## STRATEGY CALL INTELLIGENCE ({len(strategy_analyses)} calls this period)")

        all_objections: list[str] = []
        all_gaps: list[str] = []
        all_signals: list[str] = []
        all_voc: list[str] = []
        won_profiles: list[str] = []
        lost_profiles: list[str] = []

        for a in strategy_analyses:
            all_objections.extend(a.main_objections or [])
            all_gaps.extend(a.positioning_gaps or [])
            all_signals.extend(a.buying_signals or [])
            profile = a.prospect_profile
            pain_str = ", ".join((profile.main_pain_points or [])[:2])
            if a.outcome == "WON":
                won_profiles.append(f"{profile.business_type}: {pain_str}")
            elif a.outcome == "LOST":
                lost_profiles.append(f"{profile.business_type}: pain={pain_str}, objections={', '.join((a.main_objections or [])[:2])}")

        if all_objections:
            # Frequency count
            from collections import Counter
            obj_counts = Counter(all_objections)
            parts.append("Top Objections (frequency):")
            for obj, count in obj_counts.most_common(5):
                parts.append(f"  [{count}x] {obj}")

        if all_gaps:
            parts.append("Positioning Gaps (where value didn't land):")
            for gap in list(dict.fromkeys(all_gaps))[:5]:
                parts.append(f"  • {gap}")

        if all_signals:
            parts.append("Buying Signals (what's working):")
            for sig in list(dict.fromkeys(all_signals))[:5]:
                parts.append(f"  ✓ {sig}")

        if won_profiles:
            parts.append(f"Won profiles: {' | '.join(won_profiles[:3])}")
        if lost_profiles:
            parts.append(f"Lost profiles: {' | '.join(lost_profiles[:3])}")

    # ── Client review goldmine ────────────────────────────────────────────────
    client_analyses = state.get("client_review_analyses") or []
    if client_analyses:
        parts.append(f"\n## CLIENT REVIEW GOLDMINE ({len(client_analyses)} reviews)")
        for r in client_analyses[:4]:
            if r.client_wins:
                parts.append(f"  ✅ {r.client_name} ({r.client_niche}): {r.client_wins[0]}")
            if r.client_language_patterns:
                parts.append(f"     VOC: \"{r.client_language_patterns[0]}\"")
            if r.testimonial_moments:
                parts.append(f"     Quote: \"{r.testimonial_moments[0][:120]}\"")
            for angle in (r.content_angles or [])[:2]:
                parts.append(f"     💡 Content angle: [{angle.funnel_stage}] {angle.angle} → {angle.platform}")

    # ── Meta Ads signal ───────────────────────────────────────────────────────
    meta = state.get("meta_ads_report")
    if meta:
        parts.append("\n## META ADS SIGNALS (DFY)")
        parts.append(f"DFY CPL: {meta.dfy_cpl:,.1f} {meta.currency} | DFY Leads: {meta.dfy_leads} | Spend: {meta.dfy_spend:,.0f}")
        if meta.dfy_cpl > 0:
            if meta.dfy_cpl > 500:
                parts.append("⚠️ DFY CPL is high — new ad angles needed to bring cost down")
            elif meta.dfy_cpl < 150:
                parts.append("✅ DFY CPL is healthy — scale what's working, test new angles")

        # Top DFY campaigns
        dfy_campaigns = [c for c in (meta.campaigns or []) if c.offer_type.value == "DFY"]
        if dfy_campaigns:
            best = sorted(dfy_campaigns, key=lambda c: c.cpl if c.leads > 0 else 999)[:3]
            parts.append("Best DFY campaigns by CPL:")
            for c in best:
                parts.append(f"  {c.campaign_name[:50]}: {c.leads} leads @ {c.cpl:,.0f} CPL")

    # ── Training patterns ─────────────────────────────────────────────────────
    training = state.get("sales_training_analyses") or []
    if training:
        parts.append("\n## SALES TRAINING PATTERNS")
        for t in training[:2]:
            if t.patterns_identified:
                for p in t.patterns_identified[:3]:
                    parts.append(f"  Pattern: {p}")

    # ── KB context: WhatsApp sequences + content strategy ─────────────────────
    kb_context = _kb.get_content_strategy_context()
    if kb_context:
        parts.append(f"\n## EXISTING WHATSAPP SEQUENCES & CONTENT STRATEGY (from your knowledge base)")
        parts.append(kb_context[:2000])  # cap to avoid token overflow

    return "\n".join(parts)


def content_intelligence_node(state: SBITISState) -> dict:
    """
    LangGraph node: Generates the weekly DFY content intelligence report.
    """
    log.info("node.content_intelligence.start")
    errors: list[str] = []

    try:
        context = _build_content_context(state)
        full_prompt = (
            f"{_CONTENT_INTELLIGENCE_PROMPT}\n\n"
            f"{'='*60}\nSALES INTELLIGENCE DATA:\n{'='*60}\n{context}"
        )

        llm = get_llm()
        response = llm.invoke(full_prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        data = safe_json_parse(raw)

        if not data:
            raise ValueError("LLM returned empty or unparseable content strategy")

        # Parse nested ContentIdea objects
        def _parse_ideas(raw_list: list) -> list[ContentIdea]:
            out = []
            for item in (raw_list or []):
                if isinstance(item, dict):
                    try:
                        out.append(ContentIdea(**item))
                    except Exception:
                        pass
            return out

        def _parse_idea(raw_item) -> ContentIdea | None:
            if isinstance(raw_item, dict):
                try:
                    return ContentIdea(**raw_item)
                except Exception:
                    return None
            return None

        # Personal brand brief
        pb_raw = data.get("personal_brand_brief") or {}
        personal_brand = PersonalBrandBrief(
            weekly_theme=pb_raw.get("weekly_theme", ""),
            authority_post=_parse_idea(pb_raw.get("authority_post")),
            engagement_post=_parse_idea(pb_raw.get("engagement_post")),
            trust_post=_parse_idea(pb_raw.get("trust_post")),
            positioning_statement=pb_raw.get("positioning_statement", ""),
            content_to_avoid=pb_raw.get("content_to_avoid") or [],
        )

        # WhatsApp tweaks
        wa_tweaks = [
            WhatsAppMessageTweak(**t) if isinstance(t, dict) else t
            for t in (data.get("whatsapp_tweaks") or [])
        ]

        # Positioning insights
        pos_insights = [
            DFYPositioningInsight(**p) if isinstance(p, dict) else p
            for p in (data.get("positioning_insights") or [])
        ]

        report = ContentIntelligenceReport(
            report_date=state.get("run_date", ""),
            dfy_funnel_bottleneck=data.get("dfy_funnel_bottleneck", ""),
            top_objections_this_week=data.get("top_objections_this_week") or [],
            top_buying_signals=data.get("top_buying_signals") or [],
            content_ideas=_parse_ideas(data.get("content_ideas") or []),
            whatsapp_tweaks=wa_tweaks,
            positioning_insights=pos_insights,
            personal_brand_brief=personal_brand,
            meta_ad_angles=data.get("meta_ad_angles") or [],
            content_priority_this_week=data.get("content_priority_this_week", ""),
        )

        log.info(
            "node.content_intelligence.done",
            ideas=len(report.content_ideas),
            wa_tweaks=len(report.whatsapp_tweaks),
            positioning=len(report.positioning_insights),
        )
        return {"content_intelligence_report": report, "errors": errors}

    except Exception as e:
        msg = f"Content intelligence node failed: {e}"
        log.error("node.content_intelligence.failed", error=str(e))
        return {"content_intelligence_report": None, "errors": [msg]}
