"""
Knowledge Vector Store

Stores document embeddings locally using ChromaDB (persistent on disk).
Each document is chunked, embedded, and stored with metadata.

Storage path: ./knowledge_base_store/ (configurable via KB_STORE_PATH)
"""

import os
import hashlib
import structlog
from typing import Any

from ..config import config
from .drive_loader import KnowledgeDocument

log = structlog.get_logger(__name__)

# Chunk size in characters (~500 tokens at 4 chars/token)
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at a newline or sentence boundary
        if end < len(text):
            boundary = chunk.rfind("\n")
            if boundary == -1:
                boundary = chunk.rfind(". ")
            if boundary > chunk_size // 2:
                chunk = text[start: start + boundary + 1]
                end = start + boundary + 1
        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c.strip()]


def _doc_hash(content: str) -> str:
    """Hash for deduplication / change detection."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class KnowledgeVectorStore:
    """
    Persistent ChromaDB vector store for SBITIS knowledge documents.
    Uses the same Google embedding model or local embeddings.
    """

    def __init__(
        self,
        store_path: str = config.KB_STORE_PATH,
        collection_name: str = "sbitis_knowledge",
    ):
        self.store_path = store_path
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._embedder = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            from chromadb.config import Settings

            os.makedirs(self.store_path, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.store_path,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _get_embedder(self):
        """Return embedding function (Gemini or local sentence-transformers fallback)."""
        if self._embedder is None:
            if config.GEMINI_API_KEY:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=config.GEMINI_API_KEY)

                    class GeminiEmbedder:
                        def __call__(self, input: list[str]) -> list[list[float]]:
                            results = []
                            for text in input:
                                result = genai.embed_content(
                                    model="models/text-embedding-004",
                                    content=text[:8192],  # Max tokens
                                    task_type="retrieval_document",
                                )
                                results.append(result["embedding"])
                            return results

                    self._embedder = GeminiEmbedder()
                    log.info("kb.embedder", type="gemini")
                    return self._embedder
                except Exception as e:
                    log.warning("kb.gemini_embedder_failed", error=str(e))

            # Fallback: local sentence-transformers
            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer("intfloat/multilingual-e5-base")
                # Supports French, Darija (Arabic script), English

                class STEmbedder:
                    def __call__(self, input: list[str]) -> list[list[float]]:
                        return model.encode(input, normalize_embeddings=True).tolist()

                self._embedder = STEmbedder()
                log.info("kb.embedder", type="multilingual-e5-base")
            except ImportError:
                raise RuntimeError(
                    "No embedding model available. Install sentence-transformers: "
                    "pip install sentence-transformers"
                )

        return self._embedder

    def upsert_documents(self, documents: list[KnowledgeDocument]) -> int:
        """
        Add or update documents in the vector store.
        Returns number of chunks upserted.
        """
        if not documents:
            return 0

        collection = self._get_collection()
        embedder = self._get_embedder()

        total_chunks = 0
        for doc in documents:
            try:
                chunks = _chunk_text(doc.content)
                doc_hash = _doc_hash(doc.content)

                chunk_ids = []
                chunk_texts = []
                chunk_metas = []

                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc.doc_id}_chunk_{i}_{doc_hash}"
                    chunk_ids.append(chunk_id)
                    chunk_texts.append(chunk)
                    chunk_metas.append({
                        **doc.to_metadata(),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "content_hash": doc_hash,
                    })

                # Embed and upsert
                embeddings = embedder(chunk_texts)
                collection.upsert(
                    ids=chunk_ids,
                    documents=chunk_texts,
                    embeddings=embeddings,
                    metadatas=chunk_metas,
                )
                total_chunks += len(chunks)
                log.info("kb.upserted", doc=doc.title, chunks=len(chunks))

            except Exception as e:
                log.error("kb.upsert_failed", doc=doc.title, error=str(e))

        return total_chunks

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        category_filter: str | None = None,
    ) -> list[dict]:
        """
        Semantic search across the knowledge base.
        Returns list of {content, title, category, folder_path, score}.
        """
        collection = self._get_collection()
        embedder = self._get_embedder()

        try:
            # Build where clause for category filtering
            where = None
            if category_filter:
                where = {"category": {"$eq": category_filter}}

            # Embed the query
            query_embedding = embedder([query_text])[0]

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            output = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, distances):
                output.append({
                    "content": doc,
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "folder_path": meta.get("folder_path", ""),
                    "is_video": meta.get("is_video", False),
                    "video_url": meta.get("video_url", ""),
                    "similarity_score": round(1 - dist, 3),  # cosine: 1=identical
                })

            return output

        except Exception as e:
            log.error("kb.query_failed", query=query_text[:50], error=str(e))
            return []

    def get_all_by_category(self, category: str) -> list[dict]:
        """Retrieve all documents in a given category (for full-context use)."""
        collection = self._get_collection()
        try:
            results = collection.get(
                where={"category": {"$eq": category}},
                include=["documents", "metadatas"],
            )
            docs = results.get("documents") or []
            metas = results.get("metadatas") or []

            # Deduplicate by doc_id (return one chunk per doc — the first)
            seen = set()
            output = []
            for doc, meta in zip(docs, metas):
                doc_id = meta.get("doc_id", "")
                if doc_id not in seen and meta.get("chunk_index", 0) == 0:
                    seen.add(doc_id)
                    output.append({
                        "content": doc,
                        "title": meta.get("title", ""),
                        "category": category,
                        "folder_path": meta.get("folder_path", ""),
                    })
            return output
        except Exception as e:
            log.error("kb.get_by_category_failed", category=category, error=str(e))
            return []

    def count(self) -> int:
        """Return total number of chunks in the store."""
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def list_documents(self) -> list[dict]:
        """List all indexed documents (deduplicated by doc_id)."""
        collection = self._get_collection()
        try:
            results = collection.get(include=["metadatas"])
            metas = results.get("metadatas") or []
            seen = set()
            docs = []
            for meta in metas:
                doc_id = meta.get("doc_id", "")
                if doc_id not in seen:
                    seen.add(doc_id)
                    docs.append({
                        "doc_id": doc_id,
                        "title": meta.get("title", ""),
                        "category": meta.get("category", ""),
                        "folder_path": meta.get("folder_path", ""),
                        "is_video": meta.get("is_video", False),
                        "last_modified": meta.get("last_modified", ""),
                    })
            return sorted(docs, key=lambda x: x.get("category", ""))
        except Exception as e:
            log.error("kb.list_failed", error=str(e))
            return []
