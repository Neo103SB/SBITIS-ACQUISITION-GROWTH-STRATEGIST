"""Dataset 2: Sales Training & Call Review schema."""

from pydantic import BaseModel, Field
from typing import Optional


class CoachingPoint(BaseModel):
    closer: str = Field(default="", description="Name of the closer receiving coaching")
    area: str = Field(default="", description="Skill area: objection_handling, opener, close, tonality, etc.")
    issue: str = Field(default="", description="What specific issue was identified")
    evidence: str = Field(default="", description="Quote or moment from the call as evidence")
    recommendation: str = Field(default="", description="Specific improvement action")


class ActionPoint(BaseModel):
    assignee: str = Field(default="", description="Who owns this action (closer name)")
    action: str = Field(default="", description="Specific task to complete")
    deadline: str = Field(default="", description="Due date or timeframe (e.g. 'by next session')")


class SalesTrainingAnalysis(BaseModel):
    """Full structured analysis of a Sales Training / Call Review session (Dataset 2)."""

    session_id: str = Field(..., description="Fireflies transcript ID")
    session_date: str = Field(default="", description="ISO date of the session")
    session_type: str = Field(
        default="call_review",
        description="call_review | training | roleplay | mixed",
    )

    trainer: str = Field(default="Hamza", description="Name of the trainer/coach (usually Hamza)")
    participants_closers: list[str] = Field(
        default_factory=list,
        description="Names of closers present (Zineb, Chakir, Austin, etc.)",
    )

    calls_reviewed: list[str] = Field(
        default_factory=list,
        description="IDs or descriptions of specific calls discussed during this session",
    )

    key_remarks: list[str] = Field(
        default_factory=list,
        description="High-level insights and observations from the session",
    )

    coaching_points: list[CoachingPoint] = Field(
        default_factory=list,
        description="Specific feedback per closer",
    )

    action_points: list[ActionPoint] = Field(
        default_factory=list,
        description="Specific actions assigned per closer with deadlines",
    )

    scripts_or_frameworks_shared: list[str] = Field(
        default_factory=list,
        description="Any new scripts, frameworks, or techniques taught",
    )

    patterns_identified: list[str] = Field(
        default_factory=list,
        description="Systemic issues or patterns across multiple calls / closers",
    )

    fireflies_summary: str = Field(default="", description="Original Fireflies AI-generated summary")
