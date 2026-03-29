"""Fireflies.ai GraphQL client — fetches transcripts with retry logic."""

import httpx
import structlog
from datetime import datetime, timedelta, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import config

log = structlog.get_logger(__name__)

# ── GraphQL query ─────────────────────────────────────────────────────────────
TRANSCRIPTS_QUERY = """
query GetTranscripts($fromDate: String, $limit: Int) {
  transcripts(fromDate: $fromDate, limit: $limit) {
    id
    title
    date
    duration
    participants
    sentences {
      text
      speaker_name
      start_time
      end_time
    }
    summary {
      gist
      overview
      action_items
      keywords
    }
    meeting_attendees {
      displayName
      email
    }
  }
}
"""

SINGLE_TRANSCRIPT_QUERY = """
query GetTranscript($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    participants
    sentences {
      text
      speaker_name
      start_time
      end_time
    }
    summary {
      gist
      overview
      action_items
      keywords
    }
    meeting_attendees {
      displayName
      email
    }
  }
}
"""


class FirefliesClient:
    """Client for the Fireflies.ai GraphQL API."""

    def __init__(self, api_key: str = config.FIREFLIES_API_KEY):
        self.api_key = api_key
        self.url = config.FIREFLIES_GRAPHQL_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=16),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    def _post(self, query: str, variables: dict) -> dict:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.url,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise ValueError(f"GraphQL errors: {data['errors']}")
            return data

    def get_recent_transcripts(self, lookback_hours: int = config.FIREFLIES_LOOKBACK_HOURS) -> list[dict]:
        """Fetch all transcripts created in the last `lookback_hours` hours."""
        from_dt = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        from_date = from_dt.strftime("%Y-%m-%d")

        log.info("fireflies.fetch_recent", from_date=from_date, lookback_hours=lookback_hours)

        data = self._post(TRANSCRIPTS_QUERY, {"fromDate": from_date, "limit": 50})
        transcripts = data.get("data", {}).get("transcripts", []) or []

        log.info("fireflies.fetched", count=len(transcripts))
        return transcripts

    def get_transcript(self, transcript_id: str) -> dict | None:
        """Fetch a single transcript by ID."""
        try:
            data = self._post(SINGLE_TRANSCRIPT_QUERY, {"id": transcript_id})
            return data.get("data", {}).get("transcript")
        except Exception as e:
            log.error("fireflies.get_transcript_failed", id=transcript_id, error=str(e))
            return None

    @staticmethod
    def extract_full_text(transcript: dict) -> str:
        """Build a readable transcript string from sentences."""
        sentences = transcript.get("sentences") or []
        lines = []
        for s in sentences:
            speaker = s.get("speaker_name", "Unknown")
            text = s.get("text", "").strip()
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    @staticmethod
    def extract_summary(transcript: dict) -> str:
        """Extract the Fireflies AI summary as a single text block."""
        summary = transcript.get("summary") or {}
        parts = []
        if summary.get("gist"):
            parts.append(f"GIST: {summary['gist']}")
        if summary.get("overview"):
            parts.append(f"OVERVIEW: {summary['overview']}")
        if summary.get("action_items"):
            parts.append(f"ACTION ITEMS: {summary['action_items']}")
        if summary.get("keywords"):
            kw = summary["keywords"]
            if isinstance(kw, list):
                kw = ", ".join(kw)
            parts.append(f"KEYWORDS: {kw}")
        return "\n\n".join(parts)

    @staticmethod
    def get_sentence_count(transcript: dict) -> int:
        """Return number of sentences — used as reliable duration proxy."""
        return len(transcript.get("sentences") or [])

    @staticmethod
    def get_participants(transcript: dict) -> list[str]:
        """Return a clean list of participant names."""
        names = set()
        for p in transcript.get("meeting_attendees") or []:
            if p.get("displayName"):
                names.add(p["displayName"])
        for p in transcript.get("participants") or []:
            if isinstance(p, str):
                names.add(p)
        return list(names)
