"""Shared LLM helpers used across all analyst nodes."""

import json
import re
import structlog
from functools import lru_cache
from typing import Any

from ..config import config

log = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm():
    """Return the configured LLM instance (cached)."""
    if config.PRIMARY_LLM == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.CLAUDE_MODEL,
            api_key=config.ANTHROPIC_API_KEY,
            max_tokens=8192,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1,
            max_output_tokens=8192,
        )


def safe_json_parse(text: str) -> dict | None:
    """
    Robustly extract and parse a JSON object from LLM output.
    Handles markdown code blocks, trailing commas, etc.
    Returns None if parsing fails or text is empty.
    """
    if not text or not text.strip():
        return None

    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()

    # Find the first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    elif not text.strip():
        return None

    # Remove trailing commas before closing braces/brackets (common LLM error)
    text = re.sub(r",\s*([\}\]])", r"\1", text)

    try:
        result = json.loads(text)
        return result if result else None
    except json.JSONDecodeError as e:
        log.warning("json_parse_failed", error=str(e), text_snippet=text[:200])
        return None


def build_analysis_prompt(system_prompt: str, transcript: str, summary: str) -> str:
    """Standard prompt builder: system instructions + transcript + Fireflies summary."""
    return f"""{system_prompt}

---
FIREFLIES AI SUMMARY (use this as additional context):
{summary}

---
FULL TRANSCRIPT:
{transcript}

---
Respond with ONLY a valid JSON object matching the schema described above.
Do not include any explanation outside the JSON."""
