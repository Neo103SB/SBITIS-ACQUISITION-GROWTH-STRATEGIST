"""Dataset 6: Partnership Meeting schema."""

from pydantic import BaseModel, Field


class PartnershipOpportunity(BaseModel):
    type: str = Field(default="", description="referral | white_label | JV | collaboration | affiliate")
    description: str = Field(default="", description="What the opportunity entails")
    potential_value: str = Field(default="", description="Estimated revenue or strategic value")
    next_step: str = Field(default="", description="Concrete next step to advance this")
    owner: str = Field(default="", description="Who from SBITIS handles this")


class PartnershipMeetingAnalysis(BaseModel):
    """Full structured analysis of a Partnership Meeting (Dataset 6)."""

    meeting_id: str = Field(..., description="Fireflies transcript ID")
    meeting_date: str = Field(default="")
    meeting_type: str = Field(
        default="partnership_exploration",
        description="partnership_exploration | jv_discussion | referral_agreement | agency_collab",
    )

    partner_name: str = Field(default="", description="Name of the external partner or agency")
    partner_description: str = Field(default="", description="What they do, their strengths, their audience")
    sbitis_rep: str = Field(default="Hamza", description="SBITIS representative on the call")

    purpose_of_meeting: str = Field(default="", description="What was the stated reason for this meeting")

    opportunities_identified: list[PartnershipOpportunity] = Field(
        default_factory=list,
        description="Partnership opportunities surfaced",
    )

    alignment_areas: list[str] = Field(
        default_factory=list,
        description="Where both parties have shared interests or audience overlap",
    )

    concerns_or_risks: list[str] = Field(
        default_factory=list,
        description="Potential risks, misalignments, or concerns raised",
    )

    commitments_made: list[str] = Field(
        default_factory=list,
        description="Any explicit commitments or promises made on either side",
    )

    next_steps: list[str] = Field(
        default_factory=list,
        description="Follow-up actions with owners",
    )

    content_angles: list[str] = Field(
        default_factory=list,
        description="Content ideas or positioning angles surfaced",
    )

    deal_status: str = Field(
        default="exploring",
        description="exploring | active_negotiation | agreed | on_hold | dead",
    )

    fireflies_summary: str = Field(default="", description="Original Fireflies AI-generated summary")
