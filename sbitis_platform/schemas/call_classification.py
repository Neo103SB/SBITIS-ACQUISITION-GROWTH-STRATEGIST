"""Call type classification schema."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class CallType(str, Enum):
    STRATEGY_CALL = "strategy_call"            # Dataset 1 — Client-facing sales/closing
    APPOINTMENT_SETTING = "appointment_setting" # Skipped — short SDR qualification calls
    SALES_TRAINING = "sales_training"           # Dataset 2 — Internal coaching/roleplay
    LEADERSHIP_MEETING = "leadership_meeting"   # Dataset 3 — Board/strategic planning
    TEAM_MEETING = "team_meeting"               # Dataset 4 — Back/middle office ops
    CLIENT_REVIEW = "client_review"             # Dataset 5 — Monthly/bi-weekly client reviews
    PARTNERSHIP_MEETING = "partnership_meeting" # Dataset 6 — External agency/partner meetings
    UNKNOWN = "unknown"                         # Fallback — needs manual review


class ClassifiedCall(BaseModel):
    """A Fireflies transcript after classification."""

    file_id: str = Field(..., description="Fireflies transcript ID")
    title: str = Field(default="", description="Meeting title from Fireflies")
    duration_seconds: Optional[int] = Field(None, description="Reported duration (may be unreliable for .mp4 uploads)")
    sentence_count: int = Field(default=0, description="Reliable proxy for call length")
    call_type: CallType = Field(..., description="Classified call type")
    classification_method: str = Field(default="heuristic", description="'heuristic' or 'llm'")
    classification_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_transcript: str = Field(default="", description="Full transcript text")
    fireflies_summary: str = Field(default="", description="Fireflies AI-generated summary/gist")
    call_date: Optional[str] = Field(None, description="ISO date string of the meeting")
    participants: list[str] = Field(default_factory=list, description="Participant names")
    skip_deep_analysis: bool = Field(default=False, description="True for APPOINTMENT_SETTING calls")
