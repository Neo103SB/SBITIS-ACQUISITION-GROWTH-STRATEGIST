"""
KB Ingestion Node — Node 0 (runs before the main pipeline)

Syncs the Google Drive knowledge base folders into the local ChromaDB vector store.
On first run: indexes everything.
On subsequent runs: only re-indexes files modified since the last run.

This node is OPTIONAL — if Drive folders aren't configured it skips gracefully.
"""

import structlog
from datetime import datetime, timezone

from ..state import SBITISState
from ..config import config
from ..knowledge_base.drive_loader import DriveKnowledgeLoader
from ..knowledge_base.vector_store import KnowledgeVectorStore

log = structlog.get_logger(__name__)

# State file to track last ingestion time
import os
import json

_LAST_SYNC_FILE = os.path.join(config.KB_STORE_PATH, ".last_sync.json")


def _load_last_sync() -> datetime | None:
    try:
        with open(_LAST_SYNC_FILE) as f:
            data = json.load(f)
            return datetime.fromisoformat(data["last_sync"])
    except Exception:
        return None


def _save_last_sync(dt: datetime):
    os.makedirs(config.KB_STORE_PATH, exist_ok=True)
    try:
        with open(_LAST_SYNC_FILE, "w") as f:
            json.dump({"last_sync": dt.isoformat()}, f)
    except Exception as e:
        log.warning("kb_ingestion.save_sync_failed", error=str(e))


def kb_ingestion_node(state: SBITISState) -> dict:
    """
    LangGraph node: Sync Drive → ChromaDB vector store.
    Skips gracefully if no Drive folders are configured.
    """
    if not config.KB_ENABLED or not config.KNOWLEDGE_BASE_FOLDER_IDS:
        log.info("kb_ingestion.skipped", reason="disabled or no folder IDs configured")
        return {"errors": []}

    log.info("node.kb_ingestion.start", folders=len(config.KNOWLEDGE_BASE_FOLDER_IDS))
    errors: list[str] = []

    try:
        now = datetime.now(timezone.utc)
        last_sync = _load_last_sync()

        if last_sync:
            log.info("kb_ingestion.incremental", since=last_sync.isoformat())
        else:
            log.info("kb_ingestion.full_sync")

        # Load from Drive
        loader = DriveKnowledgeLoader()
        documents = loader.load_all(changed_since=last_sync)

        if not documents:
            log.info("kb_ingestion.no_new_docs")
            _save_last_sync(now)
            return {"errors": []}

        # Upsert into vector store
        store = KnowledgeVectorStore()
        total_chunks = store.upsert_documents(documents)

        _save_last_sync(now)

        log.info(
            "node.kb_ingestion.done",
            docs=len(documents),
            chunks=total_chunks,
            total_in_store=store.count(),
        )

    except Exception as e:
        msg = f"KB ingestion failed: {e}"
        log.error("node.kb_ingestion.failed", error=str(e))
        errors.append(msg)

    return {"errors": errors}
