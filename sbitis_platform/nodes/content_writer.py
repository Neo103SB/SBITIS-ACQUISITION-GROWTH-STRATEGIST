"""
Node 8 — Content Calendar Writer

Writes the Content Intelligence Report to the '🎯 DFY Content Engine' tab
in the WAR Sheet Google Spreadsheet.

Layout:
  Row 1:   ══ SBITIS DFY CONTENT ENGINE — {date} ══
  Section: Funnel Bottleneck + Top Objections
  Section: Content Ideas (ranked table)
  Section: WhatsApp Sequence Tweaks
  Section: DFY Positioning Insights
  Section: Hamza Personal Brand Brief
  Section: Meta Ad Angles to Test
"""

import structlog
from ..state import SBITISState
from ..config import config
from ..integrations.google_sheets import GoogleSheetsClient
from ..schemas.content_intelligence import ContentIntelligenceReport

log = structlog.get_logger(__name__)

CONTENT_ENGINE_TAB = "🎯 DFY Content Engine"


def _build_sheet_rows(report: ContentIntelligenceReport, run_date: str) -> list[list]:
    """Convert a ContentIntelligenceReport into Google Sheets rows."""
    rows: list[list] = []

    def header(text: str) -> list:
        return [f"━━━ {text} ━━━", "", "", "", ""]

    def row(*cells) -> list:
        return list(cells) + [""] * max(0, 5 - len(cells))

    def blank() -> list:
        return ["", "", "", "", ""]

    # ── Title ─────────────────────────────────────────────────────────────────
    rows.append([f"═══ SBITIS DFY CONTENT ENGINE — {run_date} ═══", "", "", "", ""])
    rows.append(blank())

    # ── Funnel snapshot ───────────────────────────────────────────────────────
    rows.append(header("FUNNEL BOTTLENECK"))
    rows.append(row("🚨 Bottleneck", report.dfy_funnel_bottleneck))
    rows.append(blank())

    rows.append(header("TOP OBJECTIONS THIS WEEK"))
    for i, obj in enumerate(report.top_objections_this_week, 1):
        rows.append(row(f"Objection #{i}", obj))
    rows.append(blank())

    rows.append(header("TOP BUYING SIGNALS"))
    for sig in report.top_buying_signals:
        rows.append(row("✅ Signal", sig))
    rows.append(blank())

    # ── Content Ideas ─────────────────────────────────────────────────────────
    rows.append(header("CONTENT IDEAS — RANKED BY IMPACT"))
    rows.append(["#", "Title", "Hook", "Platform", "Stage", "Data Source", "Objective"])
    for idea in sorted(report.content_ideas, key=lambda x: x.rank):
        rows.append([
            str(idea.rank),
            idea.title,
            idea.hook,
            idea.platform.value,
            idea.funnel_stage.value,
            idea.data_source,
            idea.objective,
        ])
        if idea.example_voc:
            rows.append(["", "VOC →", f'"{idea.example_voc}"', "", "", "", ""])
        if idea.format_notes:
            rows.append(["", "Format →", idea.format_notes, "", "", "", ""])
        rows.append(blank())

    # ── WhatsApp Tweaks ───────────────────────────────────────────────────────
    rows.append(header("WHATSAPP SEQUENCE TWEAKS"))
    rows.append(["Position", "Current Issue", "Suggested Rewrite", "Rationale"])
    for tweak in report.whatsapp_tweaks:
        rows.append([
            tweak.sequence_position,
            tweak.current_issue,
            tweak.suggested_rewrite,
            tweak.rationale,
        ])
        rows.append(blank())

    # ── DFY Positioning Insights ──────────────────────────────────────────────
    rows.append(header("DFY POSITIONING INSIGHTS"))
    rows.append(["Gap", "Root Cause", "Content Fix", "Ad Angle", "WA Fix"])
    for insight in report.positioning_insights:
        rows.append([
            insight.gap,
            insight.root_cause,
            insight.content_fix,
            insight.ad_angle,
            insight.whatsapp_fix,
        ])
        rows.append(blank())

    # ── Personal Brand Brief ──────────────────────────────────────────────────
    pb = report.personal_brand_brief
    rows.append(header("HAMZA PERSONAL BRAND BRIEF"))
    rows.append(row("Weekly Theme", pb.weekly_theme))
    rows.append(row("Positioning", pb.positioning_statement))
    rows.append(blank())

    for label, idea in [
        ("Authority Post", pb.authority_post),
        ("Engagement Post", pb.engagement_post),
        ("Trust / Social Proof Post", pb.trust_post),
    ]:
        if idea:
            rows.append(row(f"📌 {label}"))
            rows.append(row("  Title", idea.title))
            rows.append(row("  Hook", idea.hook))
            rows.append(row("  Angle", idea.angle))
            rows.append(row("  Platform", idea.platform.value))
            rows.append(row("  Format", idea.format_notes))
            rows.append(blank())

    if pb.content_to_avoid:
        rows.append(row("⛔ Avoid this week", " | ".join(pb.content_to_avoid)))
        rows.append(blank())

    # ── Meta Ad Angles ────────────────────────────────────────────────────────
    if report.meta_ad_angles:
        rows.append(header("META AD ANGLES TO TEST"))
        for i, angle in enumerate(report.meta_ad_angles, 1):
            rows.append(row(f"Angle #{i}", angle))
        rows.append(blank())

    # ── The One Priority ──────────────────────────────────────────────────────
    rows.append(header("CONTENT PRIORITY THIS WEEK"))
    rows.append(row("🎯 THE ONE THING", report.content_priority_this_week))
    rows.append(blank())
    rows.append(blank())

    return rows


def content_writer_node(state: SBITISState) -> dict:
    """
    LangGraph node: Writes the content intelligence report to Google Sheets.
    """
    log.info("node.content_writer.start")
    errors: list[str] = []

    report: ContentIntelligenceReport | None = state.get("content_intelligence_report")
    run_date = state.get("run_date", "UNKNOWN")

    if not report:
        log.warning("node.content_writer.no_report")
        return {"content_written": False, "errors": []}

    if config.DRY_RUN:
        log.info("node.content_writer.dry_run_skip")
        return {"content_written": False, "errors": []}

    try:
        client = GoogleSheetsClient()
        sh = client._get_spreadsheet()

        try:
            ws = sh.worksheet(CONTENT_ENGINE_TAB)
        except Exception:
            ws = sh.add_worksheet(title=CONTENT_ENGINE_TAB, rows=500, cols=8)

        new_rows = _build_sheet_rows(report, run_date)
        existing = ws.get_all_values()

        # Prepend new report — never overwrite history
        separator = [["", "", "", "", ""], ["", "", "", "", ""]]
        all_rows = new_rows + separator + existing

        ws.clear()
        ws.update("A1", all_rows)

        log.info("node.content_writer.done", rows=len(new_rows))
        return {"content_written": True, "errors": []}

    except Exception as e:
        msg = f"Content writer failed: {e}"
        log.error("node.content_writer.failed", error=str(e))
        return {"content_written": False, "errors": [msg]}
