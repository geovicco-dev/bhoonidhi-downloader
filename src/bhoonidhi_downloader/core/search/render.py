"""Rich rendering for search commands."""

import csv
import json
from pathlib import Path

from rich.align import Align
from rich.console import Console, ConsoleRenderable, Group
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from tabulate import tabulate

from bhoonidhi_downloader.viewer import Column, show_table

from .availability import (
    AVAILABILITY_DISPLAY,
    AVAILABILITY_LABEL,
    AVAILABILITY_LABEL_STYLE,
    Availability,
    availability_label,
    availability_of,
)
from .utils import (
    create_clickable_link,
    full_satellite,
    full_sensor,
    get_quicklook_url,
    get_scene_meta_url,
)


def search_columns() -> list[Column]:
    """Every search-result column, in scroll order."""
    return [
        Column("#", lambda _s, i: str(i + 1), style="dim", width=5, justify="center"),
        Column("Scene ID", lambda s, _i: s.get("ID", "N/A"), style="cyan", width=46),
        Column("Date", lambda s, _i: s.get("DOP", "N/A"), style="blue", width=13),
        Column(
            "Availability",
            lambda s, _i: availability_label(s),
            width=12,
            justify="center",
        ),
        Column(
            "Satellite", lambda s, _i: full_satellite(s), style="red", width=16
        ),
        Column("Sensor", lambda s, _i: full_sensor(s), style="blue", width=12),
        Column(
            "Product",
            lambda s, _i: f"{s.get('SELECTION', 'N/A')} ({s.get('PRODTYPE', 'N/A')})",
            style="red",
            width=34,
        ),
        Column(
            "Metadata",
            lambda s, _i: create_clickable_link(get_scene_meta_url(s), "Metadata"),
            style="blue",
            width=12,
        ),
        Column(
            "Quick View",
            lambda s, _i: create_clickable_link(get_quicklook_url(s), "Quick View"),
            style="blue",
            width=12,
        ),
    ]


def render_search_results(
    console: Console,
    scenes: list,
    slug: str | None = None,
    interactive: bool | None = None,
    header_srt: bool = False,
    filter_states: set[Availability] | None = None,
) -> None:
    """Show search results in a scrollable table.

    Every row and column can be reached — you scroll to see them. Below
    the table is a legend explaining what each Availability state means
    and what to do about it; if ``slug`` is given, it points at that
    specific saved query instead of a generic placeholder. The legend
    stays visible while scrolling as a static element.

    ``header_srt`` shows the search id in the table header — used by
    ``query create``, where every scene comes from the one fresh search.

    ``filter_states``, when given, keeps only scenes whose
    :func:`.availability.availability_of` is one of the given states —
    the "no scenes found" message distinguishes an empty result from
    everything being filtered out.
    """
    if filter_states is not None:
        scenes = [s for s in scenes if availability_of(s) in filter_states]
        if not scenes:
            console.print("[yellow]No scenes match that filter.[/]")
            return

    if not scenes:
        console.print("[yellow]No scenes found.[/]")
        return

    title = "Available Scenes"
    if header_srt:
        srts = {s.get("srt") for s in scenes if s.get("srt")}
        if len(srts) == 1:
            title = f"Available Scenes  ·  Search ID: {srts.pop()}"

    footer = _search_footer(scenes, slug)
    show_table(
        console,
        scenes,
        search_columns(),
        title,
        interactive,
        footer=footer,
    )


def _search_footer(scenes: list, slug: str | None) -> ConsoleRenderable:
    """Legend + hints shown below the table, centered to the terminal."""
    items: list[ConsoleRenderable] = []

    if any(s.get("_bhx_download") for s in scenes):
        items.append(
            Text.from_markup(
                "[green]✓[/] [dim]Already downloaded in a previous "
                "'query download' run — re-downloading will skip-fast "
                "unless --force is passed.[/]",
                justify="center",
            )
        )

    legend = _availability_legend(scenes, slug)
    if legend is not None:
        items.append(Align.center(legend))

    items.append(Rule(style="dim"))
    items.append(_link_hint())
    return Group(*items)


def _link_hint() -> Text:
    """One-line instruction on opening the Metadata/Quick View links."""
    return Text.from_markup(
        "[bold yellow]💡 Tip:[/] [italic]Cmd-click[/] [dim](macOS)[/] or "
        "[italic]Ctrl-click[/] [dim](Windows/Linux)[/] a link to open it.",
        justify="center",
    )


def _availability_legend(scenes: list, slug: str | None) -> Table | None:
    """A centered table explaining each Availability state present."""
    states = {availability_of(s) for s in scenes}
    if not states:
        return None

    table = Table(
        title="Availability Legend", show_header=False, box=None, padding=(0, 2)
    )
    table.add_column("Mark", justify="center")
    table.add_column("Meaning", justify="left")
    table.add_column("Action", justify="left")

    for state in Availability:
        if state not in states:
            continue
        meaning, action = AVAILABILITY_DISPLAY[state]
        if slug:
            action = action.replace("<slug>", slug)
        table.add_row(
            f"[{AVAILABILITY_LABEL_STYLE[state]}]{AVAILABILITY_LABEL[state]}[/]",
            f"[dim]{meaning}[/]",
            f"[cyan]{action}[/]",
        )
    return table


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
