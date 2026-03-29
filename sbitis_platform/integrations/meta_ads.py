"""Meta Ads API client — fetches campaign performance and classifies campaigns."""

import re
import structlog
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import config
from ..schemas.meta_ads import CampaignRecord, MetaAdsReport, OfferType, FunnelStage

log = structlog.get_logger(__name__)

# ── Campaign classification rules (keyword-based) ─────────────────────────────

_OFFER_PATTERNS: list[tuple[re.Pattern, OfferType]] = [
    (re.compile(r"\bDFY[_\s-]?DWY\b|\bDWY[_\s-]?DFY\b|\bsplit\b", re.I), OfferType.DFY_DWY_SPLIT),
    (re.compile(r"\bDFY\b|done.for.you|fait.pour.vous", re.I), OfferType.DFY),
    (re.compile(r"\bDWY\b|done.with.you|fait.avec", re.I), OfferType.DWY),
    (re.compile(r"\bDIY\b|do.it.yourself", re.I), OfferType.DIY),
    (re.compile(r"\bhiring\b|recrutement|recruit", re.I), OfferType.HIRING),
    (re.compile(r"\bcours\b|formation|course\b|training\b", re.I), OfferType.COURSE),
    (re.compile(r"\bbrand\b|awareness\b|notori", re.I), OfferType.BRAND_AWARENESS),
    (re.compile(r"\bstatix\b|\boleazen\b|\bclient[_\s]camp", re.I), OfferType.CLIENT_CAMPAIGN),
    (re.compile(r"\blead.?gen\b|acquisition|prospect", re.I), OfferType.CLIENT_ACQUISITION),
]

_FUNNEL_PATTERNS: list[tuple[re.Pattern, FunnelStage]] = [
    (re.compile(r"\bretarget|retargeting|reciblage", re.I), FunnelStage.RETARGETING),
    (re.compile(r"\bconversion|purchase|achat", re.I), FunnelStage.CONVERSION),
    (re.compile(r"\bbrand|awareness|notori", re.I), FunnelStage.BRAND_AWARENESS),
]

_CLIENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bstatix\b", re.I), "Statix"),
    (re.compile(r"\boleazen\b", re.I), "Oleazen"),
]


def classify_campaign(name: str) -> tuple[OfferType, FunnelStage, str | None]:
    """Classify a campaign by name into offer type, funnel stage, and optional client."""
    offer = OfferType.UNKNOWN
    for pattern, offer_type in _OFFER_PATTERNS:
        if pattern.search(name):
            offer = offer_type
            break

    funnel = FunnelStage.LEAD_GEN  # default
    for pattern, stage in _FUNNEL_PATTERNS:
        if pattern.search(name):
            funnel = stage
            break

    client = None
    if offer == OfferType.CLIENT_CAMPAIGN:
        for pattern, client_name in _CLIENT_PATTERNS:
            if pattern.search(name):
                client = client_name
                break

    return offer, funnel, client


class MetaAdsClient:
    """Wraps the Meta Business SDK to pull campaign data."""

    def __init__(
        self,
        app_id: str = config.META_APP_ID,
        app_secret: str = config.META_APP_SECRET,
        access_token: str = config.META_ACCESS_TOKEN,
        ad_account_id: str = config.META_AD_ACCOUNT_ID,
    ):
        self.ad_account_id = ad_account_id
        self._app_id = app_id
        self._app_secret = app_secret
        self._access_token = access_token
        self._sdk_initialized = False

    def _init_sdk(self):
        if self._sdk_initialized:
            return
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount  # noqa: F401
            FacebookAdsApi.init(self._app_id, self._app_secret, self._access_token)
            self._sdk_initialized = True
        except ImportError:
            raise RuntimeError(
                "facebook-business package not installed. Run: pip install facebook-business"
            )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def fetch_campaign_insights(self, days: int = config.META_REPORT_DAYS) -> MetaAdsReport:
        """Fetch campaign-level insights for the last `days` days and return a MetaAdsReport."""
        self._init_sdk()

        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adsinsights import AdsInsights

        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        date_preset_range = {
            "since": str(start_date),
            "until": str(end_date),
        }

        log.info("meta_ads.fetch_start", account=self.ad_account_id, days=days)

        account = AdAccount(self.ad_account_id)
        fields = [
            AdsInsights.Field.campaign_id,
            AdsInsights.Field.campaign_name,
            AdsInsights.Field.adset_name,
            AdsInsights.Field.spend,
            AdsInsights.Field.impressions,
            AdsInsights.Field.clicks,
            AdsInsights.Field.ctr,
            AdsInsights.Field.actions,  # contains lead events
        ]

        params = {
            "time_range": date_preset_range,
            "level": "campaign",
            "limit": 500,
        }

        insights = account.get_insights(fields=fields, params=params)

        campaigns: list[CampaignRecord] = []
        for row in insights:
            row_dict = dict(row)
            name = row_dict.get("campaign_name", "")
            offer, funnel, client = classify_campaign(name)

            # Extract leads from actions list
            leads = 0
            for action in row_dict.get("actions") or []:
                if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
                    leads += int(action.get("value", 0))

            spend = float(row_dict.get("spend", 0) or 0)
            impressions = int(row_dict.get("impressions", 0) or 0)
            clicks = int(row_dict.get("clicks", 0) or 0)
            ctr = float(row_dict.get("ctr", 0) or 0)
            cpl = spend / leads if leads > 0 else 0.0

            campaigns.append(
                CampaignRecord(
                    campaign_id=row_dict.get("campaign_id", ""),
                    campaign_name=name,
                    ad_set_name=row_dict.get("adset_name", ""),
                    offer_type=offer,
                    funnel_stage=funnel,
                    client_name=client,
                    spend=spend,
                    impressions=impressions,
                    clicks=clicks,
                    ctr=ctr,
                    leads=leads,
                    cpl=cpl,
                    date_start=str(start_date),
                    date_end=str(end_date),
                )
            )

        report = _build_report(campaigns, str(start_date), str(end_date))
        log.info(
            "meta_ads.fetch_done",
            campaigns=len(campaigns),
            total_spend=report.total_spend,
            dfy_leads=report.dfy_leads,
        )
        return report


def _build_report(campaigns: list[CampaignRecord], start: str, end: str) -> MetaAdsReport:
    """Aggregate campaign records into a MetaAdsReport."""
    totals: dict = {
        "spend": 0.0, "impressions": 0, "clicks": 0, "leads": 0,
        "dfy_spend": 0.0, "dfy_leads": 0,
        "dwy_spend": 0.0, "dwy_leads": 0,
        "brand_spend": 0.0, "brand_impressions": 0,
        "client_spend": 0.0,
    }
    offer_breakdown: dict[str, dict] = {}
    funnel_breakdown: dict[str, dict] = {}

    for c in campaigns:
        totals["spend"] += c.spend
        totals["impressions"] += c.impressions
        totals["clicks"] += c.clicks
        totals["leads"] += c.leads

        if c.offer_type == OfferType.DFY:
            totals["dfy_spend"] += c.spend
            totals["dfy_leads"] += c.leads
        elif c.offer_type == OfferType.DWY:
            totals["dwy_spend"] += c.spend
            totals["dwy_leads"] += c.leads
        elif c.offer_type == OfferType.BRAND_AWARENESS:
            totals["brand_spend"] += c.spend
            totals["brand_impressions"] += c.impressions
        elif c.offer_type == OfferType.CLIENT_CAMPAIGN:
            totals["client_spend"] += c.spend

        # Offer breakdown
        ot = c.offer_type.value
        if ot not in offer_breakdown:
            offer_breakdown[ot] = {"spend": 0.0, "leads": 0, "cpl": 0.0}
        offer_breakdown[ot]["spend"] += c.spend
        offer_breakdown[ot]["leads"] += c.leads

        # Funnel breakdown
        fs = c.funnel_stage.value
        if fs not in funnel_breakdown:
            funnel_breakdown[fs] = {"spend": 0.0, "leads": 0}
        funnel_breakdown[fs]["spend"] += c.spend
        funnel_breakdown[fs]["leads"] += c.leads

    # Compute CPL for breakdowns
    for v in offer_breakdown.values():
        v["cpl"] = v["spend"] / v["leads"] if v["leads"] > 0 else 0.0

    total_leads = totals["leads"]
    total_spend = totals["spend"]

    return MetaAdsReport(
        period_start=start,
        period_end=end,
        campaigns=campaigns,
        total_spend=total_spend,
        total_impressions=totals["impressions"],
        total_clicks=totals["clicks"],
        total_leads=total_leads,
        overall_ctr=totals["clicks"] / totals["impressions"] * 100 if totals["impressions"] > 0 else 0.0,
        overall_cpl=total_spend / total_leads if total_leads > 0 else 0.0,
        dfy_spend=totals["dfy_spend"],
        dfy_leads=totals["dfy_leads"],
        dfy_cpl=totals["dfy_spend"] / totals["dfy_leads"] if totals["dfy_leads"] > 0 else 0.0,
        dwy_spend=totals["dwy_spend"],
        dwy_leads=totals["dwy_leads"],
        dwy_cpl=totals["dwy_spend"] / totals["dwy_leads"] if totals["dwy_leads"] > 0 else 0.0,
        brand_awareness_spend=totals["brand_spend"],
        brand_awareness_impressions=totals["brand_impressions"],
        client_campaigns_spend=totals["client_spend"],
        breakdown_by_offer=offer_breakdown,
        breakdown_by_funnel=funnel_breakdown,
    )
