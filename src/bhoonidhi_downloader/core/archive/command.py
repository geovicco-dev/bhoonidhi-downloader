"""Archive command handlers."""

import json
from pathlib import Path

from rich.console import Console

from .client import ArchiveManager
from .render import render_archive_full, render_archive_satellite


def run_archive_list(console: Console, sat: str | None, refresh: bool = False) -> bool:
    """Display satellites/sensors from the archive.

    Returns True on success, False on failure.
    """
    try:
        am = ArchiveManager(refresh=refresh)
        raw_data = am.archive

        if sat:
            render_archive_satellite(console, raw_data, sat)
        else:
            render_archive_full(console, raw_data)

        return True

    except Exception as e:
        console.print(f"[bold red]Error fetching archive data:[/] {e}")
        return False


def run_archive_export(
    console: Console,
    path: str,
    sat: str | None = None,
    refresh: bool = False,
) -> bool:
    """Export archive data (optionally filtered by satellite) to a JSON file.

    Returns True on success, False on failure.
    """
    try:
        am = ArchiveManager(refresh=refresh)
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if sat:
            Path(path).write_text(json.dumps(am.parse(sat), indent=2))
            console.print(
                f"[green]Exported archive data for satellite '{sat}' to {path}[/]"
            )
            render_archive_satellite(console, am.archive, sat)
        else:
            Path(path).write_text(json.dumps(am.parse(), indent=2))
            console.print(f"[green]Exported full archive data to {path}[/]")
            render_archive_full(console, am.archive)

        return True

    except Exception as e:
        console.print(f"[bold red]Error exporting archive data:[/] {e}")
        return False
