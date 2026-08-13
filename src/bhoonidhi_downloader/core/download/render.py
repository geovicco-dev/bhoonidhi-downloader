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

from bhoonidhi_downloader.logger import CUSTOM_THEME
from bhoonidhi_downloader.viewer import Column, show_table

from ..search.utils import create_clickable_link
from .client import DownloadOutcome
from .preview import DownloadPreview

STATUS_STYLE = {
    "downloaded": "bold green",
    "already_downloaded": "cyan",
    "archived": "dim cyan",
    "skipped_on_order": "yellow",
    "skipped_priced": "magenta",
    "failed": "bold red",
}

PREVIEW_STATUS_STYLE = {
    "would_download": "bold green",
    "may_404": "dim cyan",
    "already_here": "cyan",
    "already_elsewhere": "yellow",
    "skipped_on_order": "yellow",
    "skipped_priced": "magenta",
}

PREVIEW_STATUS_LABEL = {
    "would_download": "Would download",
    "may_404": "Archived (may 404)",
    "already_here": "Already here",
    "already_elsewhere": "Already downloaded elsewhere",
    "skipped_on_order": "Skipped (on-order)",
    "skipped_priced": "Skipped (priced)",
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


def _report_columns() -> list[Column]:
    def _size(o: DownloadOutcome, _i: int) -> str:
        if not o.bytes_downloaded:
            return "-"
        return f"{o.bytes_downloaded / (1024 * 1024):.1f} MB"

    def _detail(o: DownloadOutcome, _i: int) -> str:
        if o.status == "failed":
            detail = f"[bold red]{o.error}[/]"
        elif o.status == "archived":
            detail = f"[cyan]{o.error}[/]"
        elif o.sha256:
            detail = f"{o.sha256[:16]}…"
        else:
            detail = "-"
        if o.restarted_bytes:
            restarted_mb = o.restarted_bytes / (1024 * 1024)
            detail = f"{detail} [yellow]↺ restarted ({restarted_mb:.0f} MB lost)[/]"
        return detail

    def _status(o: DownloadOutcome, _i: int) -> str:
        style = STATUS_STYLE.get(o.status, "white")
        return f"[{style}]{o.status}[/]"

    return [
        Column("Scene ID", lambda o, _i: o.scene_id, style="white", width=46),
        Column("Status", _status, width=20),
        Column("Size", _size, width=10, justify="right"),
        Column("SHA256 / Error", _detail, style="dim", width=40),
        Column("Path", lambda o, _i: o.path or "-", style="dim", width=50),
    ]


def render_download_report(
    console: Console,
    outcomes: list[DownloadOutcome],
    interactive: bool | None = None,
) -> None:
    """Render a scrollable per-scene table + status summary for a completed download batch."""
    show_table(console, outcomes, _report_columns(), "Download Report", interactive)

    counts: dict[str, int] = {}
    any_restarted = False
    for o in outcomes:
        counts[o.status] = counts.get(o.status, 0) + 1
        if o.restarted_bytes:
            any_restarted = True

    summary = ", ".join(f"{v} {k}" for k, v in counts.items())
    console.print(f"\n[bold]Summary:[/] {summary}\n")

    if any_restarted:
        console.print(
            "[yellow]Note:[/] Bhoonidhi's servers don't support resuming interrupted "
            "downloads — any scene marked '↺ restarted' had to be re-fetched from "
            "byte 0 after a prior interruption (e.g. Ctrl+C, dropped connection).\n"
        )

    if counts.get("archived"):
        portal_link = create_clickable_link(
            BHOONIDHI_BROWSE_ORDER_URL, "Bhoonidhi Browse & Order Portal"
        )
        console.print(
            "[cyan]Note:[/] scenes marked 'archived' returned HTTP 404 — the portal "
            f"has not staged them for direct download. Request them on the {portal_link} "
            "to have them made available.\n"
        )


def _preview_columns() -> list[Column]:
    def _status(p: DownloadPreview, _i: int) -> str:
        style = PREVIEW_STATUS_STYLE.get(p.status, "white")
        label = PREVIEW_STATUS_LABEL.get(p.status, p.status)
        return f"[{style}]{label}[/]"

    def _note(p: DownloadPreview, _i: int) -> str:
        return p.note or "-"

    return [
        Column("Scene ID", lambda p, _i: p.scene_id, style="white", width=46),
        Column("Status", _status, width=30),
        Column("Filename", lambda p, _i: p.filename, style="dim", width=40),
        Column("Note", _note, style="yellow", width=50),
    ]


def render_download_preview(
    console: Console,
    previews: list[DownloadPreview],
    out_dir: str,
    interactive: bool | None = None,
) -> None:
    """Render a dry-run table: what 'query download' would do, without doing it.

    Same table/summary shape as the real download report, so reading a
    dry run and reading a real run feel the same — only the verbs change.
    """
    show_table(
        console, previews, _preview_columns(), "Download Preview (dry run)", interactive
    )

    counts: dict[str, int] = {}
    for p in previews:
        counts[p.status] = counts.get(p.status, 0) + 1

    would_download = counts.get("would_download", 0) + counts.get("may_404", 0)
    console.print(
        f"\n[bold]Would attempt {would_download} download(s)[/] into {out_dir}"
    )

    summary = ", ".join(
        f"{v} {PREVIEW_STATUS_LABEL.get(k, k).lower()}" for k, v in counts.items()
    )
    if summary:
        console.print(f"[dim]{summary}[/]")

    console.print(
        "\n[dim]This is a preview only — nothing was downloaded. Re-run without "
        "--dry-run to fetch these scenes.[/]\n"
    )
