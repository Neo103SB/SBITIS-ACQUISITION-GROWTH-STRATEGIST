"""Google Sheets client — reads WAR Sheet data and writes AI Intelligence report."""

import json
import structlog
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import config
from ..state import CloserMetrics, FunnelMetrics

log = structlog.get_logger(__name__)


class GoogleSheetsClient:
    """Reads from and writes to Google Sheets via the gspread library."""

    def __init__(
        self,
        service_account_json: str = config.GOOGLE_SERVICE_ACCOUNT_JSON,
        spreadsheet_id: str = config.WAR_SHEET_ID,
    ):
        self.service_account_json = service_account_json
        self.spreadsheet_id = spreadsheet_id
        self._gc = None
        self._sheet = None

    def _get_client(self):
        if self._gc is None:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_file(self.service_account_json, scopes=scopes)
            self._gc = gspread.authorize(creds)
        return self._gc

    def _get_spreadsheet(self):
        if self._sheet is None:
            gc = self._get_client()
            self._sheet = gc.open_by_key(self.spreadsheet_id)
        return self._sheet

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def read_closer_metrics(self) -> list[CloserMetrics]:
        """Read all closer sales tracking tabs and compute metrics."""
        sh = self._get_spreadsheet()
        metrics: list[CloserMetrics] = []

        for tab_name in config.CLOSER_TABS:
            try:
                ws = sh.worksheet(tab_name)
                rows = ws.get_all_values()
                closer_name = tab_name.split(" - ")[0].strip()

                # Expected columns (1-indexed): Date, Prospect, Outcome, Revenue, Notes
                # We count rows where outcome is WON/LOST/PENDING/MAYBE
                won = lost = pending = maybe = 0
                revenue = 0.0

                for row in rows[1:]:  # skip header
                    if len(row) < 3:
                        continue
                    outcome = str(row[2]).strip().upper()
                    if outcome == "WON":
                        won += 1
                        try:
                            revenue += float(str(row[3]).replace(",", "").replace(" ", "") or 0)
                        except (ValueError, IndexError):
                            pass
                    elif outcome == "LOST":
                        lost += 1
                    elif outcome == "PENDING":
                        pending += 1
                    elif outcome in ("MAYBE", "FOLLOW UP"):
                        maybe += 1

                total_decided = won + lost
                close_rate = (won / total_decided * 100) if total_decided > 0 else 0.0

                metrics.append(
                    CloserMetrics(
                        closer_name=closer_name,
                        calls_taken=won + lost + pending + maybe,
                        won=won,
                        lost=lost,
                        pending=pending,
                        maybe=maybe,
                        close_rate=round(close_rate, 1),
                        revenue_collected=revenue,
                    )
                )
                log.info("sheets.closer_read", closer=closer_name, won=won, lost=lost)

            except Exception as e:
                log.warning("sheets.closer_tab_failed", tab=tab_name, error=str(e))

        return metrics

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def read_funnel_metrics(self) -> FunnelMetrics:
        """Read the KPIs - Ads tab for top-of-funnel metrics."""
        sh = self._get_spreadsheet()
        try:
            ws = sh.worksheet(config.KPI_ADS_TAB)
            data = ws.get_all_records()

            # Expect a key-value layout: first column = metric name, second = value
            kv: dict[str, str] = {}
            for row in data:
                vals = list(row.values())
                if len(vals) >= 2:
                    kv[str(vals[0]).strip().lower()] = str(vals[1]).strip()

            def _int(key: str) -> int:
                for k, v in kv.items():
                    if key in k:
                        try:
                            return int(str(v).replace(",", "").replace(" ", "") or 0)
                        except ValueError:
                            return 0
                return 0

            def _float(key: str) -> float:
                for k, v in kv.items():
                    if key in k:
                        try:
                            return float(str(v).replace(",", "").replace("%", "").replace(" ", "") or 0)
                        except ValueError:
                            return 0.0
                return 0.0

            leads = _int("lead")
            booked = _int("book")
            showed = _int("show")
            closed = _int("clos")
            cash = _float("cash")
            currency = "MAD"

            for k in kv:
                if "usd" in k or "$" in k:
                    currency = "USD"
                    break
                if "eur" in k or "€" in k:
                    currency = "EUR"
                    break

            return FunnelMetrics(
                leads_generated=leads,
                booked_meetings=booked,
                showed_meetings=showed,
                show_rate=round(showed / booked * 100, 1) if booked > 0 else 0.0,
                closed=closed,
                close_rate=round(closed / showed * 100, 1) if showed > 0 else 0.0,
                cash_collected=cash,
                currency=currency,
            )

        except Exception as e:
            log.error("sheets.funnel_read_failed", error=str(e))
            return FunnelMetrics(
                leads_generated=0, booked_meetings=0, showed_meetings=0,
                show_rate=0.0, closed=0, close_rate=0.0, cash_collected=0.0, currency="MAD"
            )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def write_intelligence_report(self, report_markdown: str, run_date: str) -> str:
        """
        Write the strategic report to the '🧠 AI Intelligence' tab.
        Appends a new section at the top — never overwrites prior reports.
        Returns the spreadsheet URL.
        """
        if config.DRY_RUN:
            log.info("sheets.write_skipped_dry_run")
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

        sh = self._get_spreadsheet()
        try:
            ws = sh.worksheet(config.AI_INTELLIGENCE_TAB)
        except Exception:
            # Create the tab if it doesn't exist
            ws = sh.add_worksheet(title=config.AI_INTELLIGENCE_TAB, rows=1000, cols=3)

        # Build header row and report rows
        header = [[f"═══ SBITIS INTELLIGENCE REPORT — {run_date} ═══", "", ""]]
        report_rows = [[line, "", ""] for line in report_markdown.split("\n")]
        separator = [["", "", ""], ["", "", ""]]

        # Read existing content and prepend new report
        existing = ws.get_all_values()
        new_content = header + report_rows + separator + existing

        # Clear and rewrite
        ws.clear()
        ws.update("A1", new_content)

        log.info("sheets.report_written", tab=config.AI_INTELLIGENCE_TAB, rows=len(new_content))
        return sh.url
