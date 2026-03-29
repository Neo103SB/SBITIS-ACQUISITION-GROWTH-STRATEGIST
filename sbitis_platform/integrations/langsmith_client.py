"""LangSmith dataset storage — saves structured call analyses for historical tracking."""

import json
import structlog
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import config
from ..schemas import (
    StrategyCallAnalysis,
    SalesTrainingAnalysis,
    LeadershipMeetingAnalysis,
    TeamMeetingAnalysis,
    ClientReviewAnalysis,
    PartnershipMeetingAnalysis,
)

log = structlog.get_logger(__name__)

# Dataset name → schema type mapping
DATASET_MAP = {
    config.LANGSMITH_DATASET_STRATEGY_CALLS: StrategyCallAnalysis,
    config.LANGSMITH_DATASET_SALES_TRAINING: SalesTrainingAnalysis,
    config.LANGSMITH_DATASET_LEADERSHIP: LeadershipMeetingAnalysis,
    config.LANGSMITH_DATASET_TEAM_MEETINGS: TeamMeetingAnalysis,
    config.LANGSMITH_DATASET_CLIENT_REVIEWS: ClientReviewAnalysis,
    config.LANGSMITH_DATASET_PARTNERSHIPS: PartnershipMeetingAnalysis,
}


class LangSmithStorage:
    """Manages LangSmith datasets for all 6 call analysis types."""

    def __init__(self, api_key: str = config.LANGCHAIN_API_KEY):
        self.api_key = api_key
        self._client = None
        self._datasets: dict[str, object] = {}  # name → Dataset object

    def _get_client(self):
        if self._client is None:
            from langsmith import Client
            self._client = Client(api_key=self.api_key)
        return self._client

    def _ensure_dataset(self, name: str) -> object:
        """Get or create a LangSmith dataset by name."""
        if name in self._datasets:
            return self._datasets[name]

        client = self._get_client()
        try:
            ds = client.read_dataset(dataset_name=name)
        except Exception:
            ds = client.create_dataset(
                dataset_name=name,
                description=f"SBITIS Growth Platform — {name}",
            )
            log.info("langsmith.dataset_created", name=name)

        self._datasets[name] = ds
        return ds

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def save_strategy_call(self, analysis: StrategyCallAnalysis) -> str:
        """Save a strategy call analysis to Dataset 1."""
        return self._upsert_example(
            dataset_name=config.LANGSMITH_DATASET_STRATEGY_CALLS,
            record_id=analysis.file_id,
            inputs={"file_id": analysis.file_id, "call_date": analysis.call_date},
            outputs=analysis.model_dump(),
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def save_sales_training(self, analysis: SalesTrainingAnalysis) -> str:
        return self._upsert_example(
            dataset_name=config.LANGSMITH_DATASET_SALES_TRAINING,
            record_id=analysis.session_id,
            inputs={"session_id": analysis.session_id, "session_date": analysis.session_date},
            outputs=analysis.model_dump(),
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def save_leadership_meeting(self, analysis: LeadershipMeetingAnalysis) -> str:
        return self._upsert_example(
            dataset_name=config.LANGSMITH_DATASET_LEADERSHIP,
            record_id=analysis.meeting_id,
            inputs={"meeting_id": analysis.meeting_id, "meeting_date": analysis.meeting_date},
            outputs=analysis.model_dump(),
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def save_team_meeting(self, analysis: TeamMeetingAnalysis) -> str:
        return self._upsert_example(
            dataset_name=config.LANGSMITH_DATASET_TEAM_MEETINGS,
            record_id=analysis.meeting_id,
            inputs={"meeting_id": analysis.meeting_id, "meeting_date": analysis.meeting_date},
            outputs=analysis.model_dump(),
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def save_client_review(self, analysis: ClientReviewAnalysis) -> str:
        return self._upsert_example(
            dataset_name=config.LANGSMITH_DATASET_CLIENT_REVIEWS,
            record_id=analysis.session_id,
            inputs={"session_id": analysis.session_id, "client_name": analysis.client_name},
            outputs=analysis.model_dump(),
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=16))
    def save_partnership_meeting(self, analysis: PartnershipMeetingAnalysis) -> str:
        return self._upsert_example(
            dataset_name=config.LANGSMITH_DATASET_PARTNERSHIPS,
            record_id=analysis.meeting_id,
            inputs={"meeting_id": analysis.meeting_id, "partner_name": analysis.partner_name},
            outputs=analysis.model_dump(),
        )

    def _upsert_example(
        self, dataset_name: str, record_id: str, inputs: dict, outputs: dict
    ) -> str:
        """Create or update an example in a dataset. Returns the example ID."""
        if config.DRY_RUN:
            log.info("langsmith.upsert_skipped_dry_run", dataset=dataset_name, id=record_id)
            return f"dry_run_{record_id}"

        client = self._get_client()
        ds = self._ensure_dataset(dataset_name)

        # Check if example already exists (idempotent upsert)
        try:
            examples = list(
                client.list_examples(
                    dataset_id=str(ds.id),
                    metadata={"source_id": record_id},
                    limit=1,
                )
            )
            if examples:
                client.update_example(
                    example_id=str(examples[0].id),
                    inputs=inputs,
                    outputs=outputs,
                    metadata={"source_id": record_id, "updated_at": datetime.utcnow().isoformat()},
                )
                log.info("langsmith.example_updated", dataset=dataset_name, id=record_id)
                return str(examples[0].id)
        except Exception:
            pass  # First save — fall through to create

        example = client.create_example(
            dataset_id=str(ds.id),
            inputs=inputs,
            outputs=outputs,
            metadata={"source_id": record_id, "created_at": datetime.utcnow().isoformat()},
        )
        log.info("langsmith.example_created", dataset=dataset_name, id=record_id)
        return str(example.id)

    def list_recent_strategy_calls(self, limit: int = 20) -> list[dict]:
        """Retrieve the most recent strategy call analyses for the Strategist node."""
        return self._list_recent(config.LANGSMITH_DATASET_STRATEGY_CALLS, limit)

    def list_recent_sales_training(self, limit: int = 10) -> list[dict]:
        return self._list_recent(config.LANGSMITH_DATASET_SALES_TRAINING, limit)

    def _list_recent(self, dataset_name: str, limit: int) -> list[dict]:
        if config.DRY_RUN:
            return []
        try:
            client = self._get_client()
            ds = self._ensure_dataset(dataset_name)
            examples = list(client.list_examples(dataset_id=str(ds.id), limit=limit))
            return [e.outputs or {} for e in examples]
        except Exception as e:
            log.error("langsmith.list_failed", dataset=dataset_name, error=str(e))
            return []
