"""Rich rendering for search commands."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from .utils import create_clickable_link, get_quicklook_url, get_scene_meta_url

COLD_STORAGE_THRESHOLD_DAYS = 365


def _is_likely_cold_storage(scene: dict) -> bool:
    """Heuristic: scenes older than ~1 year often age out of hot storage.

    Direct downloads for such scenes commonly 404 and need to be requested
    via the Bhoonidhi Browse & Order Portal cart first. This is a
    date-based heuristic, not a portal-confirmed status.
    """
    dop = scene.get("DOP")
    if not dop:
        return False
    try:
        acquired = datetime.strptime(dop, "%d-%b-%Y")
    except ValueError:
        return False
    return (datetime.now() - acquired) > timedelta(days=COLD_STORAGE_THRESHOLD_DAYS)


def render_search_results(console: Console, scenes: list) -> None:
    """Render search results table."""
    table = Table(title="Available Scenes")
    table.add_column("Index", style="blue")
    table.add_column("Scene ID", style="red", overflow="fold")
    table.add_column("Date", style="blue")
    table.add_column("Satellite", style="red")
    table.add_column("Sensor", style="blue")
    table.add_column("Product", style="red", overflow="fold")
    table.add_column("Access", style="blue", overflow="fold")
    table.add_column("Metadata", style="red")
    table.add_column("Quick View", style="blue")

    any_old = False
    any_downloaded = False
    for idx, scene in enumerate(scenes):
        is_old = _is_likely_cold_storage(scene)
        any_old = any_old or is_old
        date_cell = f"{scene.get('DOP', 'N/A')} ⚠" if is_old else scene.get("DOP", "N/A")

        access = scene.get("PRICED", "N/A")
        if scene.get("_bhx_download"):
            any_downloaded = True
            access = f"[green]✓ Downloaded[/] ({access})"

        table.add_row(
            str(idx + 1),
            scene.get("ID", "N/A"),
            date_cell,
            scene.get("SATELLITE", "N/A"),
            scene.get("SENSOR", "N/A"),
            f"{scene.get('SELECTION', 'N/A')} ({scene.get('PRODTYPE', 'N/A')})",
            access,
            create_clickable_link(get_scene_meta_url(scene), "View Metadata"),
            create_clickable_link(get_quicklook_url(scene), "Quick View"),
        )

    console.print(table)

    if any_downloaded:
        console.print(
            "\n[green]✓[/] [dim]Already downloaded in a previous "
            "'query download' run — re-downloading will skip-fast "
            "unless --force is passed.[/]"
        )

    if any_old:
        console.print(
            f"\n⚠  [yellow]Scenes older than {COLD_STORAGE_THRESHOLD_DAYS} days are often "
            "moved to cold storage.[/] Direct download may fail with a 404 for these — "
            "if so, request the scene via the Bhoonidhi Browse & Order Portal cart first, "
            "then retry 'query download'.",
            style="dim",
        )

    # Instructions for the user
    console.print("\nTo open table links from terminal:", style="yellow")
    console.print(
        "Click while holding Cmd (on Mac) or Ctrl (on Windows/Linux)\n", style="dim"
    )


def get_scenes_data_for_export(scenes: list) -> dict:
    """Prepare scene data for export."""
    export_data = {
        scene.get("ID", f"Unknown_{idx}"): {
            "Index": idx + 1,
            "Date": scene.get("DOP", "N/A"),
            "Satellite": scene.get("SATELLITE", "N/A"),
            "Sensor": scene.get("SENSOR", "N/A"),
            "Product": scene.get("PRODTYPE", "N/A"),
            "Metadata": get_scene_meta_url(scene),
            "Quick View": get_quicklook_url(scene),
            "Search ID": scene.get("srt", "N/A"),
        }
        for idx, scene in enumerate(scenes)
    }
    return export_data


def render_export_success(console: Console, format: str, filename: str) -> None:
    """Render export success message."""
    console.print(
        f"[green]Exported search results as {format.upper()} to {filename}.[/]"
    )


def export_search_results(
    console: Console, format: str, export_data: dict, filename: str
) -> None:
    """Export search results to file."""
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    if format == "csv":
        data = list(export_data.values())
        with open(filename, "w", newline="") as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        render_export_success(console, format, filename)

    elif format == "json":
        with open(filename, "w") as jsonfile:
            json.dump(export_data, jsonfile)
        render_export_success(console, format, filename)

    elif format == "markdown":
        data = list(export_data.values())
        headers = data[0].keys()
        table = tabulate(
            [row.values() for row in data],
            headers=headers,
            tablefmt="pipe",
        )
        with open(filename, "w") as mdfile:
            mdfile.write(table)
        render_export_success(console, format, filename)
