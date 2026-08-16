"""Rich rendering for archive commands."""

from datetime import datetime

from rich.console import Console

from bhoonidhi_downloader.schemas.selection import product_token, sat_value
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
        """Each sensor with how many distinct products it carries.

        A sensor with several dispNames (EOS-06's OCM(GAC), for example)
        bundles that many products — showing the count here is the cue to
        run ``archive list --sat X`` for the full breakdown, without
        wrapping this column into an unreadable dispName dump.
        """
        counts: dict[str, int] = {}
        for sensor in record.get("sensors") or []:
            counts[sensor.get("senName", "-")] = counts.get(
                sensor.get("senName", "-"), 0
            ) + (1 if sensor.get("dispName") else 0)
        parts = []
        for sen_name, count in counts.items():
            label = f"{count} product" if count == 1 else f"{count} products"
            parts.append(f"{sen_name} ({label})")
        return ", ".join(parts) if parts else "-"

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
        Column("Sensors", _sensors, style="blue", width=45),
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
    def _product(r: dict, _i: int) -> str:
        token = product_token(
            str(r.get("dispName", "")), r.get("satName", ""), r.get("senName", "")
        )
        # A dispName with no distinct suffix (bare "sat_sensor") IS the
        # sensor's default product; there's nothing to print, so match
        # the rest of the table's placeholder style with a dash.
        return token if token else "-"

    def _sat_flag(r: dict, _i: int) -> str:
        """The --sat value that selects exactly this row.

        A handful of sensors mix a bare, no-suffix dispName with other,
        distinctly-suffixed ones under the same sensor (some AWIFS/LISS3
        variants across the ResourceSat family) — for those, SAT:SEN
        alone resolves to every product under the sensor, not just the
        default one, so there is no --sat value that isolates the bare
        row by itself. Flag that instead of printing a value that lies.
        """
        satellite = r.get("satName", "")
        sensor = r.get("senName", "")
        token = product_token(str(r.get("dispName", "")), satellite, sensor)
        if not token:
            siblings = r.get("_sibling_products") or []
            if siblings:
                return (
                    f"[dim]no single value (SAT:SEN selects all {len(siblings) + 1})[/]"
                )
        return sat_value(satellite, sensor, token)

    return [
        Column(
            "Satellite", lambda r, _i: r.get("satName", "-"), style="cyan", width=15
        ),
        Column("Sensor", lambda r, _i: r.get("senName", "-"), style="cyan", width=14),
        Column("Product", _product, style="cyan", width=24),
        Column(
            "Resolution (m)", lambda r, _i: r.get("res", "-"), style="cyan", width=10
        ),
        Column(
            "Start Date", lambda r, _i: r.get("stDate", "-"), style="cyan", width=11
        ),
        Column(
            "End Date",
            lambda r, _i: r.get("endDate") or "Till date",
            style="cyan",
            width=11,
        ),
        Column("--sat value", _sat_flag, style="green", width=34),
    ]


def _annotate_ambiguous_defaults(rows: list[dict]) -> list[dict]:
    """Mark rows whose bare dispName can't be isolated with SAT:SEN alone.

    A row's ``_sibling_products`` lists the other dispNames sharing its
    satellite+sensor when that row itself has no distinct product suffix
    and at least one sibling does — the case where ``--sat SAT:SEN``
    resolves to more than just this row. Rows are returned as shallow
    copies so the caller's original dicts aren't mutated.
    """
    by_sat_sen: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row.get("satName", ""), row.get("senName", ""))
        by_sat_sen.setdefault(key, []).append(row)

    annotated = []
    for row in rows:
        key = (row.get("satName", ""), row.get("senName", ""))
        siblings = by_sat_sen[key]
        token = product_token(
            str(row.get("dispName", "")), row.get("satName", ""), row.get("senName", "")
        )
        other_disp_names = [
            s.get("dispName")
            for s in siblings
            if s.get("dispName") != row.get("dispName")
        ]
        new_row = dict(row)
        if not token and other_disp_names:
            new_row["_sibling_products"] = other_disp_names
        annotated.append(new_row)
    return annotated


def render_archive_satellite(
    console: Console,
    archive_data: list,
    satellite: str,
    interactive: bool | None = None,
) -> None:
    """Render a scrollable table of a single satellite's sensors and products.

    Each row is one product (one dispName) under one sensor, with the
    exact ``--sat`` value that selects it in ``bhd query create`` — copy
    it straight from this table into that command.
    """
    rows = [
        sensor
        for item in archive_data
        if item.get("satName") == satellite
        for sensor in item.get("sensors")
    ]
    rows = _annotate_ambiguous_defaults(rows)
    show_table(console, rows, _satellite_columns(), f"{satellite} Sensors", interactive)
