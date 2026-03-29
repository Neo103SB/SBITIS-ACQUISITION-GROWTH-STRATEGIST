"""Meta Ads schemas — campaign classification and KPI reporting."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class OfferType(str, Enum):
    DFY = "DFY"                          # Done For You — primary focus
    DWY = "DWY"                          # Done With You
    DIY = "DIY"                          # Do It Yourself
    DFY_DWY_SPLIT = "DFY_DWY_SPLIT"     # Split test between DFY and DWY
    HIRING = "HIRING"                    # Recruitment campaigns
    BRAND_AWARENESS = "BRAND_AWARENESS"  # Brand awareness only
    COURSE = "COURSE"                    # Formation / training product
    CLIENT_ACQUISITION = "CLIENT_ACQUISITION"  # Generic lead gen
    CLIENT_CAMPAIGN = "CLIENT_CAMPAIGN"  # Campaigns run FOR a client (e.g. Statix, Oleazen)
    UNKNOWN = "UNKNOWN"


class FunnelStage(str, Enum):
    LEAD_GEN = "LEAD_GEN"
    BRAND_AWARENESS = "BRAND_AWARENESS"
    RETARGETING = "RETARGETING"
    CONVERSION = "CONVERSION"


class CampaignRecord(BaseModel):
    """Single Meta Ads campaign with classified metadata and performance metrics."""

    campaign_id: str = Field(..., description="Meta campaign ID")
    campaign_name: str = Field(..., description="Original campaign name")
    ad_set_name: str = Field(default="", description="Ad set name if available")
    offer_type: OfferType = Field(default=OfferType.UNKNOWN, description="Classified offer type")
    funnel_stage: FunnelStage = Field(default=FunnelStage.LEAD_GEN, description="Funnel stage")
    client_name: Optional[str] = Field(None, description="If CLIENT_CAMPAIGN, which client")

    # Core metrics
    spend: float = Field(default=0.0, description="Total spend in account currency")
    impressions: int = Field(default=0)
    clicks: int = Field(default=0)
    ctr: float = Field(default=0.0, description="Click-through rate %")
    leads: int = Field(default=0, description="Lead form completions or conversions")
    cpl: float = Field(default=0.0, description="Cost per lead")

    # Status
    status: str = Field(default="ACTIVE", description="ACTIVE | PAUSED | ARCHIVED")
    date_start: str = Field(default="", description="Reporting window start")
    date_end: str = Field(default="", description="Reporting window end")


class MetaAdsReport(BaseModel):
    """Aggregated Meta Ads performance report for a given period."""

    period_start: str = Field(..., description="ISO date — report start")
    period_end: str = Field(..., description="ISO date — report end")
    currency: str = Field(default="MAD", description="Account currency")

    # All campaigns
    campaigns: list[CampaignRecord] = Field(default_factory=list)

    # Overall totals
    total_spend: float = Field(default=0.0)
    total_impressions: int = Field(default=0)
    total_clicks: int = Field(default=0)
    total_leads: int = Field(default=0)
    overall_ctr: float = Field(default=0.0)
    overall_cpl: float = Field(default=0.0)

    # DFY-specific metrics (primary focus)
    dfy_spend: float = Field(default=0.0)
    dfy_leads: int = Field(default=0)
    dfy_cpl: float = Field(default=0.0)

    # DWY-specific metrics
    dwy_spend: float = Field(default=0.0)
    dwy_leads: int = Field(default=0)
    dwy_cpl: float = Field(default=0.0)

    # Brand awareness
    brand_awareness_spend: float = Field(default=0.0)
    brand_awareness_impressions: int = Field(default=0)

    # Client campaigns (not SBITIS cost center)
    client_campaigns_spend: float = Field(default=0.0)

    # Breakdown by offer type (dict: OfferType -> metrics dict)
    breakdown_by_offer: dict = Field(
        default_factory=dict,
        description="Spend, leads, CPL keyed by OfferType value",
    )

    # Breakdown by funnel stage
    breakdown_by_funnel: dict = Field(
        default_factory=dict,
        description="Spend, leads keyed by FunnelStage value",
    )
