"""Rich rendering for archive commands."""

from datetime import datetime

from rich.console import Console
from rich.table import Table


def render_archive_full(console: Console, archive_data: list) -> None:
    """Render full archive table."""
    table = Table(title="Bhoonidhi Browse & Order Archive")
    table.add_column("Index", style="blue")
    table.add_column("Satellite", style="red")
    table.add_column("Availability", style="blue")
    table.add_column("Access Level", style="red")
    table.add_column("Sensors", style="blue", overflow="fold")
    table.add_column("Resolution (m)", style="red")

    if len(archive_data) != 0:
        for idx, record in enumerate(archive_data):
            res_range = (
                f"{record.get('thisMinRes')} - {record.get('thisMaxRes')}"
                if record.get("thisMinRes") != record.get("thisMaxRes")
                else record.get("thisMinRes")
            )

            availability = (
                f"{datetime.strptime(record.get('totalStartDate'), '%m/%d/%Y').strftime('%d %B %Y')} - "
                f"{datetime.strptime(record.get('totalEndDate'), '%m/%d/%Y').strftime('%d %B %Y')}"
                if record.get("totalEndDate") != ""
                else f"{datetime.strptime(record.get('totalStartDate'), '%m/%d/%Y').strftime('%d %B %Y')} - till date"
            )

            sensors_list = [r.get("senName") for r in record.get("sensors")]
            sensors = ", ".join(sensors_list)

            table.add_row(
                str(idx + 1),
                record.get("satName", "N/A"),
                availability,
                record.get("priced", "N/A").split("_")[-1],
                sensors,
                res_range,
            )

        console.print(table)


def render_archive_satellite(
    console: Console, archive_data: list, satellite: str
) -> None:
    """Render archive filtered by satellite."""
    # Filter archive data based on satellite
    data = [
        item.get("sensors") for item in archive_data if item.get("satName") == satellite
    ]

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Satellite", style="cyan")
    table.add_column("Sensor", style="cyan")
    table.add_column("Display Name", style="cyan", overflow="fold")
    table.add_column("Resolution (m)", style="cyan")
    table.add_column("Start Date", style="cyan")
    table.add_column("End Date", style="cyan")
    table.add_column("Products", style="cyan", overflow="fold")

    # Add rows
    for d in data:
        for i in d:
            if i.get("endDate") == "":
                i["endDate"] = "Till date"
            table.add_row(
                i.get("satName", "-"),
                i.get("senName", "-"),
                i.get("dispName", "-"),
                i.get("res", "-"),
                i.get("stDate", "-"),
                i.get("endDate", "-"),
                i.get("products", "-"),
            )
    console.print(table)
