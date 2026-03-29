"""Dataset 1: Strategy Call (Client-Facing Sales/Closing) schema."""

from pydantic import BaseModel, Field
from typing import Optional


class ProspectProfile(BaseModel):
    business_type: str = Field(default="", description="Industry / niche of the prospect's business")
    current_situation: str = Field(default="", description="Where they are right now — revenue, team size, challenges")
    main_pain_points: list[str] = Field(default_factory=list, description="Top pain points expressed")


class KeyMoment(BaseModel):
    timestamp_approx: str = Field(default="", description="Approximate timestamp or context marker")
    description: str = Field(default="", description="What happened and why it matters")


class StrategyCallAnalysis(BaseModel):
    """Full structured analysis of a Strategy Call (Dataset 1)."""

    # Identifiers
    file_id: str = Field(..., description="Fireflies transcript ID")
    call_date: str = Field(default="", description="ISO date of the call")
    closer_name: str = Field(default="", description="Name of the SBITIS closer on the call")
    prospect_name: str = Field(default="", description="Name or handle of the prospect")

    # Outcome
    outcome: str = Field(
        default="PENDING",
        description="WON | LOST | PENDING | MAYBE",
        pattern="^(WON|LOST|PENDING|MAYBE)$",
    )
    duration_estimate: str = Field(default="", description="Short / Medium / Long based on sentence count")
    language_detected: str = Field(
        default="Mix",
        description="French | Darija | Mix | English",
    )

    # Prospect intelligence
    prospect_profile: ProspectProfile = Field(default_factory=ProspectProfile)

    # Offer
    value_offer: str = Field(default="", description="The specific offer pitched (DFY / DWY / DIY / etc.)")
    currency: str = Field(
        default="MAD",
        description="MAD | USD | EUR — currency used when discussing pricing",
        pattern="^(MAD|USD|EUR)$",
    )
    ghl_tag: str = Field(default="", description="GoHighLevel tag assigned to this contact (DFY, DWY, etc.)")

    # Objections
    main_objections: list[str] = Field(default_factory=list, description="Specific objections raised by the prospect")
    objection_handling: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Score 1–10: how well the closer handled objections",
    )
    objection_handling_notes: str = Field(default="", description="Detailed notes on objection handling quality")

    # Positioning
    positioning_gaps: list[str] = Field(
        default_factory=list,
        description="Where the value didn't land / weak spots in pitch",
    )

    # Buying signals
    buying_signals: list[str] = Field(default_factory=list, description="Positive signals from the prospect")

    # Close quality
    close_attempt: str = Field(default="", description="How and when the closer tried to close")
    close_quality: int = Field(default=5, ge=1, le=10, description="Score 1–10 for close quality")
    close_quality_notes: str = Field(default="", description="Notes on the close quality")

    # Key moments
    key_moments: list[KeyMoment] = Field(default_factory=list, description="Critical moments in the call")

    # Coaching
    recommended_improvements: list[str] = Field(
        default_factory=list,
        description="Specific, actionable coaching points for the closer",
    )

    # Fireflies context
    fireflies_summary: str = Field(default="", description="Original Fireflies AI-generated gist/overview")
