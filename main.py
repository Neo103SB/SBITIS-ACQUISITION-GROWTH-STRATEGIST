"""
SBITIS Growth Intelligence Platform — Entry Point

Run modes:
  python main.py            → Single run (now)
  python main.py --schedule → Run on cron schedule (default: 07:00 daily)
  python main.py --dry-run  → Dry run (no writes to Sheets or LangSmith)
  python main.py --date YYYY-MM-DD → Override run date
"""

import argparse
import os
import sys
import structlog
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

log = structlog.get_logger(__name__)
console = Console()


def configure_logging(level: str = "INFO"):
    import logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )


def run_pipeline(run_date: str | None = None, dry_run: bool = False) -> dict:
    """Execute a full pipeline run and return the final state."""
    from sbitis_platform.graph import graph, create_initial_state
    from sbitis_platform.config import config

    if dry_run:
        os.environ["DRY_RUN"] = "true"

    initial_state = create_initial_state(run_date)

    console.print(
        Panel(
            Text.from_markup(
                f"[bold cyan]SBITIS Growth Intelligence Platform[/bold cyan]\n"
                f"Run ID: [yellow]{initial_state['run_id']}[/yellow]\n"
                f"Date: [green]{initial_state['run_date']}[/green]\n"
                f"Dry Run: [{'yellow' if dry_run else 'green'}]{dry_run}[/{'yellow' if dry_run else 'green'}]"
            ),
            title="▶ Starting Pipeline",
            border_style="cyan",
        )
    )

    log.info(
        "pipeline.start",
        run_id=initial_state["run_id"],
        run_date=initial_state["run_date"],
        dry_run=dry_run,
    )

    try:
        final_state = graph.invoke(initial_state)

        # ── Summary output ────────────────────────────────────────────────
        errors = final_state.get("errors") or []
        stored = len(final_state.get("langsmith_stored_ids") or [])
        report_written = final_state.get("report_written", False)
        sheet_url = final_state.get("report_sheet_url", "")
        strategy_calls = len(final_state.get("strategy_call_analyses") or [])
        classified = len(final_state.get("classified_calls") or [])

        status_color = "green" if report_written and not errors else ("yellow" if errors else "red")

        console.print(
            Panel(
                Text.from_markup(
                    f"[bold]Transcripts classified:[/bold] {classified}\n"
                    f"[bold]Strategy calls analyzed:[/bold] {strategy_calls}\n"
                    f"[bold]LangSmith records stored:[/bold] {stored}\n"
                    f"[bold]Report written:[/bold] {'✅' if report_written else '❌'}\n"
                    f"[bold]Sheet URL:[/bold] {sheet_url or 'N/A'}\n"
                    f"[bold]Errors:[/bold] {len(errors)}"
                    + (f"\n[red]{'\\n'.join(errors[:5])}[/red]" if errors else ""),
                ),
                title=f"[{status_color}]✓ Pipeline Complete[/{status_color}]",
                border_style=status_color,
            )
        )

        if final_state.get("strategic_report"):
            console.print("\n[bold cyan]═══ STRATEGIC REPORT PREVIEW (first 500 chars) ═══[/bold cyan]")
            console.print(final_state["strategic_report"][:500] + "...")

        log.info(
            "pipeline.complete",
            classified=classified,
            strategy_calls=strategy_calls,
            stored=stored,
            report_written=report_written,
            errors=len(errors),
        )

        return final_state

    except Exception as e:
        console.print(f"[bold red]PIPELINE FAILED: {e}[/bold red]")
        log.error("pipeline.fatal_error", error=str(e))
        raise


def run_scheduled(schedule_time: str = "07:00"):
    """Run the pipeline on a daily schedule."""
    import schedule
    import time

    console.print(f"[cyan]Scheduling daily run at {schedule_time}...[/cyan]")

    def job():
        try:
            run_pipeline()
        except Exception as e:
            log.error("scheduled_run.failed", error=str(e))

    schedule.every().day.at(schedule_time).do(job)

    console.print(f"[green]Scheduler running. Next run at {schedule_time} daily. Ctrl+C to stop.[/green]")
    while True:
        schedule.run_pending()
        import time as _time
        _time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SBITIS Growth Intelligence Platform")
    parser.add_argument("--schedule", action="store_true", help="Run on daily schedule")
    parser.add_argument("--schedule-time", default="07:00", help="Time for daily run (HH:MM, default: 07:00)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run — no writes to Sheets or LangSmith")
    parser.add_argument("--date", type=str, default=None, help="Override run date (YYYY-MM-DD)")
    parser.add_argument("--log-level", default="INFO", help="Log level: DEBUG, INFO, WARNING, ERROR")
    args = parser.parse_args()

    configure_logging(args.log_level)

    if args.schedule:
        run_scheduled(args.schedule_time)
    else:
        run_pipeline(run_date=args.date, dry_run=args.dry_run)
