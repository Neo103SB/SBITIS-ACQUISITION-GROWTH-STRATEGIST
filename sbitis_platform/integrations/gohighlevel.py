"""GoHighLevel CRM client — fetches pipeline and contact data."""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import config

log = structlog.get_logger(__name__)


class GoHighLevelClient:
    """Thin wrapper around the GHL REST API v2."""

    def __init__(
        self,
        api_key: str = config.GHL_API_KEY,
        location_id: str = config.GHL_LOCATION_ID,
        base_url: str = config.GHL_BASE_URL,
    ):
        self.api_key = api_key
        self.location_id = location_id
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=16),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    def _get(self, path: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                params=params or {},
            )
            response.raise_for_status()
            return response.json()

    def get_pipeline_summary(self) -> dict:
        """
        Return a summary of contacts across pipelines, grouped by stage and tag.
        Focuses on DFY and DWY tags relevant to SBITIS acquisition funnels.
        """
        try:
            pipelines_data = self._get(
                f"/opportunities/search",
                params={"location_id": self.location_id, "limit": 100},
            )

            opportunities = pipelines_data.get("opportunities") or []

            summary: dict = {
                "total_opportunities": len(opportunities),
                "by_stage": {},
                "by_tag": {},
                "by_closer": {},
                "recent_won": [],
                "recent_lost": [],
            }

            for opp in opportunities:
                stage = opp.get("pipelineStage", {}).get("name", "Unknown")
                summary["by_stage"][stage] = summary["by_stage"].get(stage, 0) + 1

                tags = opp.get("contact", {}).get("tags") or []
                for tag in tags:
                    summary["by_tag"][tag] = summary["by_tag"].get(tag, 0) + 1

                assignee = (opp.get("assignedTo") or {}).get("name", "Unassigned")
                summary["by_closer"][assignee] = summary["by_closer"].get(assignee, 0) + 1

                status = opp.get("status", "")
                if status == "won":
                    summary["recent_won"].append(
                        {
                            "name": opp.get("contact", {}).get("name", ""),
                            "value": opp.get("monetaryValue", 0),
                            "date": opp.get("updatedAt", ""),
                        }
                    )
                elif status == "lost":
                    summary["recent_lost"].append(
                        {
                            "name": opp.get("contact", {}).get("name", ""),
                            "date": opp.get("updatedAt", ""),
                            "lost_reason": opp.get("lostReason", ""),
                        }
                    )

            # Limit recent lists
            summary["recent_won"] = sorted(
                summary["recent_won"], key=lambda x: x["date"], reverse=True
            )[:10]
            summary["recent_lost"] = sorted(
                summary["recent_lost"], key=lambda x: x["date"], reverse=True
            )[:10]

            log.info(
                "ghl.pipeline_summary",
                total=summary["total_opportunities"],
                stages=len(summary["by_stage"]),
            )
            return summary

        except Exception as e:
            log.error("ghl.pipeline_summary_failed", error=str(e))
            return {"error": str(e), "total_opportunities": 0}

    def get_contact_tag(self, contact_id: str) -> list[str]:
        """Fetch the tags for a specific contact (used to enrich call analyses)."""
        try:
            data = self._get(f"/contacts/{contact_id}")
            return data.get("contact", {}).get("tags") or []
        except Exception as e:
            log.warning("ghl.contact_tag_failed", contact_id=contact_id, error=str(e))
            return []
