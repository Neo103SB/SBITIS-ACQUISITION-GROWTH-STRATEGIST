"""Dataset 4: Team Meeting (Back/Middle Office) schema."""

from pydantic import BaseModel, Field


class ClientIssue(BaseModel):
    client_name: str = Field(default="")
    issue: str = Field(default="")
    severity: str = Field(default="medium", description="low | medium | high | critical")
    owner: str = Field(default="")
    resolution_plan: str = Field(default="")


class TeamActionPoint(BaseModel):
    assignee: str = Field(default="")
    department: str = Field(default="", description="media_buying | content | video | ops | all")
    action: str = Field(default="")
    deadline: str = Field(default="")
    priority: str = Field(default="medium", description="low | medium | high | urgent")


class TeamMeetingAnalysis(BaseModel):
    """Full structured analysis of a Team Meeting — back/middle office (Dataset 4)."""

    meeting_id: str = Field(..., description="Fireflies transcript ID")
    meeting_date: str = Field(default="")
    team: str = Field(
        default="mixed",
        description="media_buying | content | video | ops | mixed",
    )

    attendees: list[str] = Field(default_factory=list)

    executive_summary: str = Field(default="", description="2-3 sentence overview")

    client_issues: list[ClientIssue] = Field(
        default_factory=list,
        description="Delivery / performance issues raised about specific clients",
    )

    operational_issues: list[str] = Field(
        default_factory=list,
        description="Internal process or system issues flagged",
    )

    action_points: list[TeamActionPoint] = Field(
        default_factory=list,
        description="Tasks assigned with owners and deadlines",
    )

    wins_celebrated: list[str] = Field(
        default_factory=list,
        description="Positive outcomes, wins, or milestones mentioned",
    )

    content_angles: list[str] = Field(
        default_factory=list,
        description="Content ideas or marketing angles surfaced",
    )

    fireflies_summary: str = Field(default="", description="Original Fireflies AI-generated summary")
