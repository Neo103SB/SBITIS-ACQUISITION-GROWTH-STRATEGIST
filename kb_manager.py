"""
Knowledge Base Manager CLI

Standalone tool to manage the SBITIS knowledge base without running the full pipeline.

Commands:
  python kb_manager.py sync          — Sync Drive folders into vector store
  python kb_manager.py sync --full   — Force full re-index (ignore last sync time)
  python kb_manager.py list          — List all indexed documents
  python kb_manager.py search "..."  — Semantic search
  python kb_manager.py stats         — Show store stats
"""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def cmd_sync(full: bool = False):
    """Sync Google Drive folders into the vector store."""
    from sbitis_platform.knowledge_base.drive_loader import DriveKnowledgeLoader
    from sbitis_platform.knowledge_base.vector_store import KnowledgeVectorStore
    from sbitis_platform.config import config

    if not config.KNOWLEDGE_BASE_FOLDER_IDS:
        console.print("[red]No KB_FOLDER_IDS configured in .env[/red]")
        console.print("Add folder IDs from your Google Drive URLs.")
        sys.exit(1)

    console.print(Panel(
        f"[cyan]Syncing {len(config.KNOWLEDGE_BASE_FOLDER_IDS)} Drive folder(s)...[/cyan]\n"
        f"Mode: {'[yellow]FULL RE-INDEX[/yellow]' if full else '[green]INCREMENTAL[/green]'}",
        title="KB Sync"
    ))

    from sbitis_platform.nodes.kb_ingestion import _load_last_sync, _save_last_sync
    from datetime import datetime, timezone

    changed_since = None if full else _load_last_sync()
    if changed_since:
        console.print(f"  Checking for files modified since: {changed_since.isoformat()}")

    loader = DriveKnowledgeLoader()
    documents = loader.load_all(changed_since=changed_since)

    if not documents:
        console.print("[yellow]No new or changed documents found.[/yellow]")
        return

    store = KnowledgeVectorStore()
    total_chunks = store.upsert_documents(documents)
    _save_last_sync(datetime.now(timezone.utc))

    console.print(f"\n[green]✅ Indexed {len(documents)} documents → {total_chunks} chunks[/green]")
    console.print(f"[dim]Total chunks in store: {store.count()}[/dim]")

    # Show what was indexed
    table = Table(title="Indexed Documents", show_lines=True)
    table.add_column("Title", style="cyan", max_width=40)
    table.add_column("Category", style="yellow")
    table.add_column("Type", style="green")
    table.add_column("Folder")

    for doc in documents:
        table.add_row(
            doc.title,
            doc.category,
            "🎥 Video" if doc.is_video else "📄 Doc",
            doc.folder_path[:40],
        )
    console.print(table)


def cmd_list():
    """List all indexed documents."""
    from sbitis_platform.knowledge_base.vector_store import KnowledgeVectorStore
    store = KnowledgeVectorStore()

    docs = store.list_documents()
    if not docs:
        console.print("[yellow]Knowledge base is empty. Run: python kb_manager.py sync[/yellow]")
        return

    table = Table(title=f"Knowledge Base — {len(docs)} Documents", show_lines=True)
    table.add_column("Category", style="yellow", width=20)
    table.add_column("Title", style="cyan", max_width=45)
    table.add_column("Type", width=8)
    table.add_column("Modified", width=12)

    for doc in sorted(docs, key=lambda x: (x.get("category", ""), x.get("title", ""))):
        table.add_row(
            doc.get("category", ""),
            doc.get("title", ""),
            "🎥" if doc.get("is_video") else "📄",
            (doc.get("last_modified") or "")[:10],
        )
    console.print(table)
    console.print(f"\n[dim]Total chunks in vector store: {store.count()}[/dim]")


def cmd_search(query: str, n: int = 5, category: str | None = None):
    """Semantic search across the knowledge base."""
    from sbitis_platform.knowledge_base.retriever import KnowledgeRetriever
    retriever = KnowledgeRetriever()

    console.print(f"\n[cyan]Searching: '{query}'[/cyan]" + (f" [category: {category}]" if category else ""))

    store = retriever._store
    results = store.query(query, n_results=n, category_filter=category)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    for i, r in enumerate(results, 1):
        console.print(Panel(
            f"[bold]{r['title']}[/bold]\n"
            f"[dim]Category: {r['category']} | Score: {r['similarity_score']} | {r['folder_path']}[/dim]\n\n"
            + (f"🎥 Video: {r.get('video_url', '')}\n" if r.get("is_video") else "")
            + r["content"][:400] + ("..." if len(r["content"]) > 400 else ""),
            title=f"Result {i}",
            border_style="cyan" if r["similarity_score"] > 0.7 else "dim",
        ))


def cmd_stats():
    """Show knowledge base statistics."""
    from sbitis_platform.knowledge_base.vector_store import KnowledgeVectorStore
    from sbitis_platform.config import config
    from sbitis_platform.nodes.kb_ingestion import _load_last_sync

    store = KnowledgeVectorStore()
    docs = store.list_documents()
    last_sync = _load_last_sync()

    # Group by category
    categories: dict = {}
    for doc in docs:
        cat = doc.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    table = Table(title="Knowledge Base Statistics")
    table.add_column("Category", style="yellow")
    table.add_column("Documents", justify="right", style="cyan")

    for cat, count in sorted(categories.items()):
        table.add_row(cat, str(count))

    console.print(Panel(
        f"Total Documents: [bold cyan]{len(docs)}[/bold cyan]\n"
        f"Total Chunks: [bold cyan]{store.count()}[/bold cyan]\n"
        f"Last Sync: [bold green]{last_sync.isoformat() if last_sync else 'Never'}[/bold green]\n"
        f"Store Path: [dim]{config.KB_STORE_PATH}[/dim]\n"
        f"Drive Folders: [dim]{len(config.KNOWLEDGE_BASE_FOLDER_IDS)} configured[/dim]",
        title="KB Stats"
    ))
    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SBITIS Knowledge Base Manager")
    sub = parser.add_subparsers(dest="command")

    # sync
    sync_p = sub.add_parser("sync", help="Sync Drive folders into vector store")
    sync_p.add_argument("--full", action="store_true", help="Force full re-index")

    # list
    sub.add_parser("list", help="List all indexed documents")

    # search
    search_p = sub.add_parser("search", help="Semantic search")
    search_p.add_argument("query", type=str)
    search_p.add_argument("-n", type=int, default=5)
    search_p.add_argument("--category", type=str, default=None,
                          help="Filter by category: sop | sales_framework | training | video | whatsapp_sequence")

    # stats
    sub.add_parser("stats", help="Show store statistics")

    args = parser.parse_args()

    if args.command == "sync":
        cmd_sync(full=getattr(args, "full", False))
    elif args.command == "list":
        cmd_list()
    elif args.command == "search":
        cmd_search(args.query, n=args.n, category=args.category)
    elif args.command == "stats":
        cmd_stats()
    else:
        parser.print_help()
