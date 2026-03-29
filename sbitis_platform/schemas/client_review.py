"""Dataset 5: Client Coaching / Review schema — content goldmine."""

from pydantic import BaseModel, Field
from typing import Optional


class ResultAchieved(BaseModel):
    metric: str = Field(default="", description="What metric was measured (ROAS, leads, CPL, etc.)")
    value: str = Field(default="", description="The actual value or result")
    period: str = Field(default="", description="Time period for this result")
    vs_target: str = Field(default="", description="How this compares to target")


class ContentAngle(BaseModel):
    angle: str = Field(default="", description="The specific content angle or story")
    format_suggestion: str = Field(
        default="",
        description="Recommended format: reel, carousel, long-form, email, etc.",
    )
    platform: str = Field(default="", description="Instagram | YouTube | WhatsApp | LinkedIn")
    funnel_stage: str = Field(
        default="",
        description="TOFU | MOFU | BOFU — which stage of funnel this serves",
    )
    rationale: str = Field(default="", description="Why this angle would resonate (backed by client data)")


class ClientReviewAnalysis(BaseModel):
    """Full structured analysis of a Client Coaching / Review session (Dataset 5)."""

    session_id: str = Field(..., description="Fireflies transcript ID")
    session_date: str = Field(default="")
    session_type: str = Field(
        default="monthly_review",
        description="monthly_review | bi_weekly_review | coaching | onboarding | offboarding",
    )

    client_name: str = Field(default="", description="Client business / contact name")
    client_niche: str = Field(default="", description="Client's industry / niche")
    sbitis_account_manager: str = Field(default="", description="SBITIS team member on the call")

    results_achieved: list[ResultAchieved] = Field(
        default_factory=list,
        description="Concrete results discussed in the review",
    )

    client_wins: list[str] = Field(
        default_factory=list,
        description="Positive outcomes and transformations celebrated",
    )

    client_challenges: list[str] = Field(
        default_factory=list,
        description="Remaining challenges or friction the client faces",
    )

    client_language_patterns: list[str] = Field(
        default_factory=list,
        description="Exact phrases / words the client uses to describe their situation (voice of customer)",
    )

    content_angles: list[ContentAngle] = Field(
        default_factory=list,
        description="Specific content angles derived from this review — the goldmine",
    )

    testimonial_moments: list[str] = Field(
        default_factory=list,
        description="Moments or quotes usable as social proof / testimonials",
    )

    upsell_signals: list[str] = Field(
        default_factory=list,
        description="Signals that client may be ready for an upsell or expansion",
    )

    action_points: list[str] = Field(
        default_factory=list,
        description="Follow-up actions from this review",
    )

    fireflies_summary: str = Field(default="", description="Original Fireflies AI-generated summary")
