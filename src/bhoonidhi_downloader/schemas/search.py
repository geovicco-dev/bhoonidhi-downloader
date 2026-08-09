from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, model_validator

from bhoonidhi_downloader.schemas import AOISchema

from ..core.archive.client import ArchiveManager

# ── module-level lazy cache (NOT a class variable) ──
_manifest = None  # type: dict[str, dict[str, list[dict]]] | None


def _parse_date(s: str | None) -> datetime | None:
    """Parse 'MM/DD/YYYY' or return None."""
    return datetime.strptime(s, "%m/%d/%Y") if s else None


def _get_manifest() -> dict[str, dict[str, list[dict]]]:
    """Build manifest once, cache at module level."""
    global _manifest
    if _manifest is None:
        _manifest = ArchiveManager().build_manifest()
    return _manifest


class SearchSchema(BaseModel):
    aoi: AOISchema = Field(default_factory=AOISchema, description="Area of Interest")
    satellite: str | None = Field(
        default="ResourceSat-2A", description="Satellite name"
    )
    sensor: str | None = Field(default="LISS3", description="Sensor name")
    start_date: datetime = Field(
        default=datetime.now(timezone.utc) - timedelta(days=30),
        description="Start date (YYYY-MM-DD)",
    )
    end_date: datetime = Field(
        default=datetime.now(timezone.utc),
        description="End date (YYYY-MM-DD)",
    )

    @model_validator(mode="after")
    def validate_aoi_bounds(self) -> "SearchSchema":
        """Validate that AOI bounding box is well-formed and within EPSG:4326 limits."""
        # ── Well-formedness ──────────────────────────────────────────
        if self.aoi.min_lon >= self.aoi.max_lon:
            raise ValueError(
                f"Invalid bounding box: min_lon ({self.aoi.min_lon}) must be "
                f"less than max_lon ({self.aoi.max_lon})."
            )
        if self.aoi.min_lat >= self.aoi.max_lat:
            raise ValueError(
                f"Invalid bounding box: min_lat ({self.aoi.min_lat}) must be "
                f"less than max_lat ({self.aoi.max_lat})."
            )

        # ── EPSG:4326 coordinate limits ──────────────────────────────
        if not (-180 <= self.aoi.min_lon <= 180):
            raise ValueError(
                f"min_lon ({self.aoi.min_lon}) is outside valid EPSG:4326 range [-180, 180]."
            )
        if not (-180 <= self.aoi.max_lon <= 180):
            raise ValueError(
                f"max_lon ({self.aoi.max_lon}) is outside valid EPSG:4326 range [-180, 180]."
            )
        if not (-90 <= self.aoi.min_lat <= 90):
            raise ValueError(
                f"min_lat ({self.aoi.min_lat}) is outside valid EPSG:4326 range [-90, 90]."
            )
        if not (-90 <= self.aoi.max_lat <= 90):
            raise ValueError(
                f"max_lat ({self.aoi.max_lat}) is outside valid EPSG:4326 range [-90, 90]."
            )

        return self

    @model_validator(mode="after")
    def validate_date_range(self) -> "SearchSchema":
        """Validate that start_date is not after end_date."""
        if self.start_date > self.end_date:
            raise ValueError(
                f"Start date ({self.start_date.date()}) cannot be after "
                f"end date ({self.end_date.date()})."
            )
        return self

    @model_validator(mode="after")
    def validate_satellite_and_sensor(self) -> "SearchSchema":
        manifest = _get_manifest()

        # ── Satellite / sensor existence ───────────────────────────
        if self.satellite and self.satellite not in manifest:
            available = sorted(manifest.keys())
            raise ValueError(
                f"Invalid satellite '{self.satellite}'. Available: {available}"
            )

        if self.sensor and not self.satellite:
            raise ValueError("sensor cannot be provided without satellite")

        if self.satellite and self.sensor:
            satellite_sensors = _get_manifest().get(self.satellite, {})
            if self.sensor not in satellite_sensors:
                available = sorted(satellite_sensors.keys())
                raise ValueError(
                    f"Invalid sensor '{self.sensor}' for satellite '{self.satellite}'. "
                    f"Available sensors: {available}"
                )

        # ── Date-range validation ──────────────────────────────────
        if self.satellite and self.sensor:
            products = _get_manifest()[self.satellite][self.sensor]

            # Compute the overall valid window (earliest start → latest end)
            all_starts = [
                d
                for d in (
                    _parse_date(p["startDate"]) for p in products if p.get("startDate")
                )
                if d is not None
            ]
            all_ends = [
                d
                for d in (
                    _parse_date(p["endDate"])
                    for p in products
                    if p.get("endDate") is not None
                )
                if d is not None
            ]

            earliest_start = min(all_starts) if all_starts else None
            latest_end = max(all_ends) if all_ends else None  # None = ongoing

            # Check user's window against the sensor's window
            if earliest_start and self.start_date < earliest_start:
                raise ValueError(
                    f"Search start_date ({self.start_date.date()}) is before "
                    f"the earliest data for {self.satellite}/{self.sensor} "
                    f"({earliest_start.strftime('%Y-%m-%d')})"
                )

            if latest_end and self.end_date > latest_end:
                raise ValueError(
                    f"Search end_date ({self.end_date.date()}) is after "
                    f"the latest data for {self.satellite}/{self.sensor} "
                    f"({latest_end.strftime('%Y-%m-%d')})"
                )

        return self
