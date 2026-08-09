"""Rich rendering for download commands: progress bars + summary report."""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from bhoonidhi_downloader.logger import CUSTOM_THEME

from ..search.utils import create_clickable_link
from .client import DownloadOutcome

STATUS_STYLE = {
    "downloaded": "bold green",
    "already_downloaded": "cyan",
    "skipped_priced": "yellow",
    "cold_storage": "bold magenta",
    "failed": "bold red",
}

BHOONIDHI_BROWSE_ORDER_URL = "https://bhoonidhi.nrsc.gov.in/bhoonidhi/index.html#"


def make_progress() -> Progress:
    """Multi-task progress display for concurrent scene downloads.

    Deliberately does NOT reuse the app's shared console — that one has a
    hardcoded ``width=300`` (see ``logger.get_console``, needed elsewhere to
    avoid wrapping wide scene-ID table rows). Rich's ``Live`` redraws a
    progress display in place by computing how many terminal rows to move
    the cursor up and clear; if the console's reported width doesn't match
    the real terminal, that math is wrong and every refresh prints a new
    frame instead of overwriting the last one — the duplicated-line mess
    seen with even a single download. A fresh, auto-sized console (same
    theme, no forced width) fixes redraw-in-place.
    """
    progress_console = Console(theme=CUSTOM_THEME, force_terminal=True)
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[scene_id]}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=progress_console,
        transient=False,
    )


def render_download_report(console: Console, outcomes: list[DownloadOutcome]) -> None:
    """Render a per-scene table + status summary for a completed download batch."""
    table = Table(title="Download Report")
    table.add_column("Scene ID", style="white", overflow="fold")
    table.add_column("Status")
    table.add_column("Size", justify="right")
    table.add_column("SHA256 / Error", style="dim", overflow="fold")
    table.add_column("Path", style="dim", overflow="fold")

    counts: dict[str, int] = {}
    any_restarted = False
    for o in outcomes:
        counts[o.status] = counts.get(o.status, 0) + 1
        style = STATUS_STYLE.get(o.status, "white")
        size = (
            f"{o.bytes_downloaded / (1024 * 1024):.1f} MB"
            if o.bytes_downloaded
            else "-"
        )
        if o.status == "failed":
            detail = f"[bold red]{o.error}[/]"
        elif o.status == "cold_storage":
            detail = f"[magenta]{o.error}[/]"
        elif o.sha256:
            detail = f"{o.sha256[:16]}…"
        else:
            detail = "-"
        if o.restarted_bytes:
            any_restarted = True
            restarted_mb = o.restarted_bytes / (1024 * 1024)
            detail = f"{detail}\n[yellow]↺ restarted from scratch ({restarted_mb:.0f} MB lost)[/]"
        table.add_row(
            o.scene_id,
            f"[{style}]{o.status}[/]",
            size,
            detail,
            o.path or "-",
        )

    console.print(table)

    summary = ", ".join(f"{v} {k}" for k, v in counts.items())
    console.print(f"\n[bold]Summary:[/] {summary}\n")

    if any_restarted:
        console.print(
            "[yellow]Note:[/] Bhoonidhi's servers don't support resuming interrupted "
            "downloads — any scene marked '↺ restarted' had to be re-fetched from "
            "byte 0 after a prior interruption (e.g. Ctrl+C, dropped connection).\n"
        )

    if counts.get("cold_storage"):
        portal_link = create_clickable_link(
            BHOONIDHI_BROWSE_ORDER_URL, "Bhoonidhi Browse & Order Portal"
        )
        console.print(
            "[magenta]Note:[/] scenes marked 'cold_storage' returned HTTP 404. Bhoonidhi's "
            "archiving policy isn't publicly documented, but scenes this old typically aren't "
            f"served directly. Request them on the {portal_link} — this CLI only fetches "
            "OpenData_DirectDownload scenes and has no cart/order support yet (metadata only).\n"
        )
