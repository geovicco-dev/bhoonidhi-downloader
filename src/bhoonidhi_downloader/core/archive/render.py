"""Rich rendering for archive commands."""

from datetime import datetime

from rich.console import Console

from bhoonidhi_downloader.viewer import Column, show_table


def _full_columns() -> list[Column]:
    def _availability(record: dict, _i: int) -> str:
        start = datetime.strptime(record.get("totalStartDate"), "%m/%d/%Y").strftime(
            "%d %B %Y"
        )
        if record.get("totalEndDate") == "":
            return f"{start} - till date"
        end = datetime.strptime(record.get("totalEndDate"), "%m/%d/%Y").strftime(
            "%d %B %Y"
        )
        return f"{start} - {end}"

    def _resolution(record: dict, _i: int) -> str:
        min_res = record.get("thisMinRes")
        max_res = record.get("thisMaxRes")
        return f"{min_res} - {max_res}" if min_res != max_res else min_res

    def _sensors(record: dict, _i: int) -> str:
        return ", ".join(r.get("senName") for r in record.get("sensors"))

    return [
        Column("#", lambda _r, i: str(i + 1), style="blue", width=5, justify="right"),
        Column(
            "Satellite", lambda r, _i: r.get("satName", "N/A"), style="red", width=15
        ),
        Column("Availability", _availability, style="blue", width=35),
        Column(
            "Access Level",
            lambda r, _i: r.get("priced", "N/A").split("_")[-1],
            style="red",
            width=12,
        ),
        Column("Sensors", _sensors, style="blue", width=40),
        Column("Resolution (m)", _resolution, style="red", width=15),
    ]


def render_archive_full(
    console: Console, archive_data: list, interactive: bool | None = None
) -> None:
    """Render the full archive in a scrollable table."""
    if not archive_data:
        return
    show_table(
        console,
        archive_data,
        _full_columns(),
        "Bhoonidhi Browse & Order Archive",
        interactive,
    )


def _satellite_columns() -> list[Column]:
    return [
        Column(
            "Satellite", lambda r, _i: r.get("satName", "-"), style="cyan", width=15
        ),
        Column("Sensor", lambda r, _i: r.get("senName", "-"), style="cyan", width=10),
        Column(
            "Display Name", lambda r, _i: r.get("dispName", "-"), style="cyan", width=20
        ),
        Column(
            "Resolution (m)", lambda r, _i: r.get("res", "-"), style="cyan", width=15
        ),
        Column(
            "Start Date", lambda r, _i: r.get("stDate", "-"), style="cyan", width=12
        ),
        Column(
            "End Date",
            lambda r, _i: r.get("endDate") or "Till date",
            style="cyan",
            width=12,
        ),
        Column(
            "Products", lambda r, _i: r.get("products", "-"), style="cyan", width=25
        ),
    ]


def render_archive_satellite(
    console: Console,
    archive_data: list,
    satellite: str,
    interactive: bool | None = None,
) -> None:
    """Render a scrollable table of a single satellite's sensors."""
    rows = [
        sensor
        for item in archive_data
        if item.get("satName") == satellite
        for sensor in item.get("sensors")
    ]
    show_table(console, rows, _satellite_columns(), f"{satellite} Sensors", interactive)
