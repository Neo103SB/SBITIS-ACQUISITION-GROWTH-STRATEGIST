"""
Node 6 — Output Writer

Writes the final strategic report to the '🧠 AI Intelligence' tab
in the Google Sheets WAR Sheet. Never overwrites existing data.
"""

import structlog
from ..state import SBITISState
from ..integrations.google_sheets import GoogleSheetsClient
from ..config import config

log = structlog.get_logger(__name__)


def output_writer_node(state: SBITISState) -> dict:
    """
    LangGraph node: Writes the strategic report to Google Sheets.
    """
    log.info("node.output_writer.start")
    errors: list[str] = []

    report = state.get("strategic_report") or ""
    run_date = state.get("run_date", "UNKNOWN")

    if not report:
        msg = "No strategic report to write — strategist produced empty output"
        log.warning("node.output_writer.empty_report")
        return {"report_written": False, "report_sheet_url": "", "errors": [msg]}

    try:
        client = GoogleSheetsClient()
        url = client.write_intelligence_report(report, run_date)

        log.info("node.output_writer.done", url=url, run_date=run_date)
        return {
            "report_written": True,
            "report_sheet_url": url,
            "errors": [],
        }

    except Exception as e:
        msg = f"Output writer failed: {e}"
        log.error("node.output_writer.failed", error=str(e))
        return {
            "report_written": False,
            "report_sheet_url": "",
            "errors": [msg],
        }
