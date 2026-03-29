"""Dataset 3: Leadership / Board Meeting schema."""

from pydantic import BaseModel, Field


class IssueItem(BaseModel):
    category: str = Field(default="", description="Domain: sales, ops, hiring, product, finance, etc.")
    description: str = Field(default="", description="The issue or challenge identified")
    owner: str = Field(default="", description="Person responsible for resolving it")


class GoalItem(BaseModel):
    goal: str = Field(default="", description="Stated goal or objective")
    timeframe: str = Field(default="", description="When this should be achieved")
    owner: str = Field(default="", description="Who owns this goal")
    metric: str = Field(default="", description="How success will be measured")


class DecisionMade(BaseModel):
    decision: str = Field(default="", description="Decision that was made")
    rationale: str = Field(default="", description="Why this decision was made")
    impact: str = Field(default="", description="Expected business impact")


class LeadershipMeetingAnalysis(BaseModel):
    """Full structured analysis of a Leadership / Board Meeting (Dataset 3)."""

    meeting_id: str = Field(..., description="Fireflies transcript ID")
    meeting_date: str = Field(default="", description="ISO date")
    meeting_type: str = Field(
        default="leadership",
        description="leadership | board | quarterly_review | planning_session",
    )

    attendees: list[str] = Field(default_factory=list)

    executive_summary: str = Field(default="", description="2-3 sentence summary of the session")

    goals_discussed: list[GoalItem] = Field(
        default_factory=list,
        description="Goals or targets discussed",
    )

    issues_raised: list[IssueItem] = Field(
        default_factory=list,
        description="Problems or blockers identified",
    )

    decisions_made: list[DecisionMade] = Field(
        default_factory=list,
        description="Key decisions taken in this meeting",
    )

    next_steps: list[str] = Field(
        default_factory=list,
        description="Concrete next steps / follow-ups with owners",
    )

    strategic_priorities: list[str] = Field(
        default_factory=list,
        description="Top strategic priorities coming out of this meeting",
    )

    content_angles: list[str] = Field(
        default_factory=list,
        description="Potential content angles / marketing ideas surfaced",
    )

    fireflies_summary: str = Field(default="", description="Original Fireflies AI-generated summary")
