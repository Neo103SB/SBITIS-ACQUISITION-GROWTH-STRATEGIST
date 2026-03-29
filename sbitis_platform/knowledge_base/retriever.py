"""
Knowledge Retriever

High-level interface used by analyst nodes and the Strategist to pull
relevant context from the knowledge base.

Each query type is tailored to what that node actually needs:
  - strategy_call_analyst → sales frameworks, objection handling SOPs
  - training_analyst      → coaching frameworks, scripts
  - strategist            → all SOPs, frameworks, strategic docs
"""

import structlog
from .vector_store import KnowledgeVectorStore

log = structlog.get_logger(__name__)

# How many chunks to retrieve per query
DEFAULT_N = 4


class KnowledgeRetriever:
    """Retrieves relevant knowledge base context for LLM prompts."""

    def __init__(self, store: KnowledgeVectorStore | None = None):
        self._store = store or KnowledgeVectorStore()

    def _format_results(self, results: list[dict]) -> str:
        """Format retrieval results into a clean context block for LLM injection."""
        if not results:
            return ""

        lines = ["--- RELEVANT KNOWLEDGE BASE CONTEXT ---"]
        for r in results:
            lines.append(f"\n📄 [{r['category'].upper()}] {r['title']}")
            if r.get("folder_path"):
                lines.append(f"   Source: {r['folder_path']}")
            lines.append(r["content"])
            lines.append("---")

        return "\n".join(lines)

    def get_strategy_call_context(self, objections: list[str] | None = None) -> str:
        """
        Retrieve sales frameworks and objection handling context
        for strategy call analysis.
        """
        if self._store.count() == 0:
            return ""

        queries = [
            "closing framework sales process SBITIS",
            "objection handling price too expensive",
            "DFY offer positioning value proposition",
        ]
        if objections:
            queries.append(" ".join(objections[:3]))

        results = []
        seen_titles = set()
        for q in queries:
            for r in self._store.query(q, n_results=2):
                if r["title"] not in seen_titles and r["similarity_score"] > 0.5:
                    results.append(r)
                    seen_titles.add(r["title"])
                    if len(results) >= DEFAULT_N:
                        break

        return self._format_results(results[:DEFAULT_N])

    def get_training_context(self) -> str:
        """Retrieve coaching frameworks and sales scripts for training analysis."""
        if self._store.count() == 0:
            return ""

        results = []
        seen = set()

        for q in ["sales training coaching framework", "call review process closer feedback"]:
            for r in self._store.query(q, n_results=3, category_filter="sales_framework"):
                if r["title"] not in seen:
                    results.append(r)
                    seen.add(r["title"])

        # Also pull SOPs
        for r in self._store.query("sales coaching SOP", n_results=2, category_filter="SOP"):
            if r["title"] not in seen:
                results.append(r)
                seen.add(r["title"])

        return self._format_results(results[:DEFAULT_N])

    def get_strategist_context(self) -> str:
        """
        Retrieve broad strategic context for the Strategist node.
        Pulls top SOPs, frameworks, and strategic docs.
        """
        if self._store.count() == 0:
            return ""

        results = []
        seen = set()

        priority_queries = [
            "SBITIS growth strategy acquisition funnel",
            "DFY offer sales process closing rate",
            "Meta ads lead generation ROAS targets",
            "team structure roles responsibilities",
            "WhatsApp follow-up sequence qualification",
        ]

        for q in priority_queries:
            for r in self._store.query(q, n_results=2):
                if r["title"] not in seen and r["similarity_score"] > 0.45:
                    results.append(r)
                    seen.add(r["title"])
                    if len(results) >= 8:
                        break

        return self._format_results(results[:8])

    def get_content_strategy_context(self) -> str:
        """
        Retrieve content strategy and WhatsApp sequence context
        for client review and content recommendation nodes.
        """
        if self._store.count() == 0:
            return ""

        results = []
        seen = set()

        for q in [
            "WhatsApp follow-up message sequence",
            "Instagram content strategy funnel stage",
            "content angles hooks video script",
            "personal brand positioning",
        ]:
            for r in self._store.query(q, n_results=2):
                if r["title"] not in seen:
                    results.append(r)
                    seen.add(r["title"])

        return self._format_results(results[:DEFAULT_N])

    def get_onboarding_context(self, topic: str = "") -> str:
        """
        Retrieve onboarding videos and training materials by topic.
        Returns video links + text docs relevant to the topic.
        """
        if self._store.count() == 0:
            return ""

        query = f"onboarding training {topic}".strip()
        results = self._store.query(query, n_results=6)

        # Include videos (they have video_url)
        lines = []
        for r in results:
            if r.get("is_video"):
                lines.append(f"🎥 VIDEO: {r['title']} → {r.get('video_url', 'link unavailable')}")
            else:
                lines.append(f"📄 DOC: {r['title']}\n{r['content'][:400]}...")

        return "\n".join(lines) if lines else ""

    def get_agency_brain(self, max_chars: int = 8000) -> str:
        """
        Always-on Agency Brain context — injected into EVERY strategic LLM call.

        Unlike other retrieval methods (which are semantic/query-based), this
        returns ALL documents in the `agency_brain` category unconditionally.
        These docs define how the model should THINK about SBITIS: vision,
        positioning, DFY philosophy, Hamza's brand, coach frameworks.

        max_chars: cap to avoid overflowing the context window (default 8k chars).
        """
        if self._store.count() == 0:
            return ""

        # Fetch all agency_brain docs — no similarity threshold, no query
        results = self._store.query(
            "SBITIS agency vision positioning DFY philosophy",
            n_results=20,
            category_filter="agency_brain",
        )

        if not results:
            return ""

        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║               SBITIS AGENCY BRAIN — ALWAYS ON               ║",
            "║  This is the core identity, philosophy, and positioning of   ║",
            "║  SBITIS ACQUISITION. Reason through this lens at all times.  ║",
            "╚══════════════════════════════════════════════════════════════╝",
        ]

        total_chars = sum(len(l) for l in lines)
        for r in results:
            block = f"\n### {r['title']}\n{r['content']}\n"
            if total_chars + len(block) > max_chars:
                break
            lines.append(block)
            total_chars += len(block)

        return "\n".join(lines)

    def search(self, query: str, n: int = 5, category: str | None = None) -> str:
        """Free-form search — usable from CLI or ad-hoc queries."""
        results = self._store.query(query, n_results=n, category_filter=category)
        return self._format_results(results)
