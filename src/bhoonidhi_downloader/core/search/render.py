"""Rich rendering for search commands."""

import csv
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from .availability import (
    AVAILABILITY_DISPLAY,
    AVAILABILITY_LABEL,
    AVAILABILITY_LABEL_STYLE,
    Availability,
    availability_label,
    availability_of,
)
from .utils import create_clickable_link, get_quicklook_url, get_scene_meta_url


def render_search_results(console: Console, scenes: list, slug: str | None = None) -> None:
    """Render the search results table.

    The Availability column shows ``Ready``, ``Archived``, ``OnOrder`` or
    ``Priced``, with a legend below giving each one's meaning and the
    action it needs. When ``slug`` is given, the legend's download hint
    names that query directly instead of the generic ``<slug>`` placeholder.
    """
    table = Table(title="Available Scenes", title_style="bold")
    table.add_column("Index", style="dim", justify="center")
    table.add_column("Scene ID", style="cyan", overflow="fold", justify="left")
    table.add_column("Date", style="blue", justify="center")
    # No column style: availability_label() styles each cell by its state.
    table.add_column("Availability", overflow="fold", justify="center")
    table.add_column("Satellite", style="red", justify="center")
    table.add_column("Sensor", style="blue", justify="center")
    table.add_column("Product", style="red", overflow="fold", justify="center")
    table.add_column("Metadata", style="blue", justify="center")
    table.add_column("Quick View", style="blue", justify="center")

    any_downloaded = False
    for idx, scene in enumerate(scenes):
        if scene.get("_bhx_download"):
            any_downloaded = True

        table.add_row(
            str(idx + 1),
            scene.get("ID", "N/A"),
            scene.get("DOP", "N/A"),
            availability_label(scene),
            scene.get("SATELLITE", "N/A"),
            scene.get("SENSOR", "N/A"),
            f"{scene.get('SELECTION', 'N/A')} ({scene.get('PRODTYPE', 'N/A')})",
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

    _render_availability_legend(console, {availability_of(s) for s in scenes}, slug)

    console.print(
        "\n  [yellow]Cmd-click[/] [dim](macOS)[/] or [yellow]Ctrl-click[/] "
        "[dim](Windows/Linux)[/] [dim]to open table links.[/]\n"
    )


def _render_availability_legend(
    console: Console, states: set[Availability], slug: str | None = None
) -> None:
    """Print a key for the Availability states present in the results."""
    if not states:
        return

    console.print()
    for state in Availability:
        if state not in states:
            continue
        meaning, action = AVAILABILITY_DISPLAY[state]
        if slug:
            action = action.replace("<slug>", slug)
        # Pad before styling: markup would otherwise count toward the width.
        label = f"{AVAILABILITY_LABEL[state]:<10}"
        console.print(
            f"  [{AVAILABILITY_LABEL_STYLE[state]}]{label}[/]"
            f"[dim]{meaning:<24}[/][cyan]{action}[/]"
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
