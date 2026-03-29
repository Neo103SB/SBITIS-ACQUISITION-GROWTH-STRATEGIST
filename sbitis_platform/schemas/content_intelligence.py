"""Schemas for the Content Intelligence Layer."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class FunnelStage(str, Enum):
    TOFU = "TOFU"   # Top of Funnel — attract strangers
    MOFU = "MOFU"   # Middle — nurture, build trust
    BOFU = "BOFU"   # Bottom — pre-close, eliminate objections


class ContentPlatform(str, Enum):
    INSTAGRAM_REEL = "Instagram Reel"
    INSTAGRAM_CAROUSEL = "Instagram Carousel"
    INSTAGRAM_STORY = "Instagram Story"
    YOUTUBE_SHORT = "YouTube Short"
    YOUTUBE_LONG = "YouTube Long-Form"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"


class ContentIdea(BaseModel):
    """A single data-backed content idea."""
    rank: int = Field(..., description="Priority rank (1 = most impactful)")
    title: str = Field(..., description="Working title for this piece of content")
    hook: str = Field(..., description="The opening line / scroll-stopping hook")
    angle: str = Field(..., description="The specific angle or narrative framing")
    platform: ContentPlatform
    funnel_stage: FunnelStage
    format_notes: str = Field(default="", description="Format guidance: length, structure, CTA")
    data_source: str = Field(
        default="",
        description="What data/insight drives this idea (e.g. 'top objection: prix', 'client win: 3x ROAS')"
    )
    objective: str = Field(
        default="",
        description="What this content should accomplish (pre-frame, overcome objection, build trust, etc.)"
    )
    example_voc: str = Field(
        default="",
        description="Voice-of-customer quote to use as inspiration or direct content"
    )


class WhatsAppMessageTweak(BaseModel):
    """Suggested improvement to a WhatsApp follow-up message."""
    sequence_position: str = Field(
        default="",
        description="Which message in the sequence (e.g. 'Message 1 — Day 0', 'Reminder — Day 2')"
    )
    current_issue: str = Field(default="", description="What's not working in the current message")
    suggested_rewrite: str = Field(default="", description="Suggested improved version of the message")
    rationale: str = Field(default="", description="Why this change should improve show rate or response")


class DFYPositioningInsight(BaseModel):
    """How to better position DFY based on call intelligence."""
    gap: str = Field(default="", description="Where DFY value isn't landing in calls")
    root_cause: str = Field(default="", description="Why prospects don't get it")
    content_fix: str = Field(default="", description="What content would pre-frame this before the call")
    ad_angle: str = Field(default="", description="Meta ad angle that addresses this gap")
    whatsapp_fix: str = Field(default="", description="WhatsApp sequence message that handles this pre-call")


class PersonalBrandBrief(BaseModel):
    """Weekly personal brand content brief for Hamza."""
    weekly_theme: str = Field(default="", description="The overarching theme for this week's content")
    authority_post: ContentIdea | None = Field(
        None,
        description="One long-form post that establishes authority (YouTube or Instagram carousel)"
    )
    engagement_post: ContentIdea | None = Field(
        None,
        description="One high-engagement post (reel, polarizing opinion, story)"
    )
    trust_post: ContentIdea | None = Field(
        None,
        description="One social proof or results post (case study, client testimonial)"
    )
    positioning_statement: str = Field(
        default="",
        description="How to position Hamza this week vs the market (what makes SBITIS DFY different)"
    )
    content_to_avoid: list[str] = Field(
        default_factory=list,
        description="Content angles or topics to avoid this week (based on market saturation or off-brand)"
    )


class ContentIntelligenceReport(BaseModel):
    """Full weekly content intelligence output."""

    report_date: str = Field(default="", description="ISO date of this report")
    dfy_funnel_bottleneck: str = Field(
        default="",
        description="The #1 funnel bottleneck for DFY right now (from data)"
    )
    top_objections_this_week: list[str] = Field(
        default_factory=list,
        description="Top 3 objections from strategy calls this week"
    )
    top_buying_signals: list[str] = Field(
        default_factory=list,
        description="What's actually converting — positive patterns"
    )
    content_ideas: list[ContentIdea] = Field(
        default_factory=list,
        description="Ranked content ideas for the week (aim for 5-8)"
    )
    whatsapp_tweaks: list[WhatsAppMessageTweak] = Field(
        default_factory=list,
        description="Specific WhatsApp sequence improvements"
    )
    positioning_insights: list[DFYPositioningInsight] = Field(
        default_factory=list,
        description="DFY positioning gaps and how to fix them via content"
    )
    personal_brand_brief: PersonalBrandBrief = Field(
        default_factory=PersonalBrandBrief,
        description="Hamza's weekly personal brand brief"
    )
    meta_ad_angles: list[str] = Field(
        default_factory=list,
        description="Specific new Meta ad angles to test based on call insights"
    )
    content_priority_this_week: str = Field(
        default="",
        description="THE ONE content priority this week — single sentence"
    )
