"""
Node 3 — Data Aggregator

Pulls live data from 3 sources in parallel:
  1. Meta Ads API (campaign performance with DFY/DWY breakdown)
  2. Google Sheets WAR Sheet (closer metrics + funnel KPIs)
  3. GoHighLevel CRM (pipeline summary)
"""

import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..state import SBITISState
from ..integrations.meta_ads import MetaAdsClient
from ..integrations.google_sheets import GoogleSheetsClient
from ..integrations.gohighlevel import GoHighLevelClient
from ..config import config

log = structlog.get_logger(__name__)


def data_aggregator_node(state: SBITISState) -> dict:
    """
    LangGraph node: Fetches Meta Ads data, WAR Sheet metrics, and GHL pipeline.
    Runs all 3 fetches concurrently for speed.
    """
    log.info("node.data_aggregator.start")
    errors: list[str] = []

    meta_report = None
    closer_metrics = []
    funnel_metrics = None
    ghl_summary = {}

    # ── Run all 3 data sources concurrently ──────────────────────────────────
    def fetch_meta():
        try:
            client = MetaAdsClient()
            return client.fetch_campaign_insights(days=config.META_REPORT_DAYS)
        except Exception as e:
            log.error("node.data_aggregator.meta_failed", error=str(e))
            return None, str(e)

    def fetch_sheets():
        try:
            client = GoogleSheetsClient()
            closers = client.read_closer_metrics()
            funnel = client.read_funnel_metrics()
            return closers, funnel, None
        except Exception as e:
            log.error("node.data_aggregator.sheets_failed", error=str(e))
            return [], None, str(e)

    def fetch_ghl():
        try:
            client = GoHighLevelClient()
            return client.get_pipeline_summary(), None
        except Exception as e:
            log.error("node.data_aggregator.ghl_failed", error=str(e))
            return {}, str(e)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_meta): "meta",
            executor.submit(fetch_sheets): "sheets",
            executor.submit(fetch_ghl): "ghl",
        }

        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()

                if source == "meta":
                    if isinstance(result, tuple):
                        err_report, err_msg = result
                        errors.append(f"Meta Ads: {err_msg}")
                    else:
                        meta_report = result
                        log.info(
                            "node.data_aggregator.meta_done",
                            spend=meta_report.total_spend,
                            dfy_leads=meta_report.dfy_leads,
                        )

                elif source == "sheets":
                    closer_m, funnel_m, err_msg = result
                    if err_msg:
                        errors.append(f"Google Sheets: {err_msg}")
                    else:
                        closer_metrics = closer_m
                        funnel_metrics = funnel_m
                        log.info(
                            "node.data_aggregator.sheets_done",
                            closers=len(closer_metrics),
                            leads=funnel_m.get("leads_generated", 0) if funnel_m else 0,
                        )

                elif source == "ghl":
                    ghl_data, err_msg = result
                    if err_msg:
                        errors.append(f"GHL: {err_msg}")
                    else:
                        ghl_summary = ghl_data
                        log.info(
                            "node.data_aggregator.ghl_done",
                            opps=ghl_data.get("total_opportunities", 0),
                        )

            except Exception as e:
                errors.append(f"{source} future error: {e}")
                log.error("node.data_aggregator.future_error", source=source, error=str(e))

    log.info(
        "node.data_aggregator.done",
        meta_ok=meta_report is not None,
        sheets_ok=len(closer_metrics) > 0,
        ghl_ok=bool(ghl_summary),
        errors=len(errors),
    )

    return {
        "meta_ads_report": meta_report,
        "closer_metrics": closer_metrics,
        "funnel_metrics": funnel_metrics,
        "ghl_pipeline_summary": ghl_summary,
        "errors": errors,
    }
