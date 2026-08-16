from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, model_validator

from bhoonidhi_downloader.schemas import AOISchema
from bhoonidhi_downloader.schemas.selection import Selection


class SearchSchema(BaseModel):
    aoi: AOISchema = Field(default_factory=AOISchema, description="Area of Interest")
    selections: list[Selection] = Field(
        default_factory=lambda: [Selection(satellite="ResourceSat-2A", sensor="LISS3")],
        description="One or more satellite/sensor/product targets to search",
    )
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
        """Validate the AOI is well-formed for whichever mode it's in."""
        if self.aoi.mode == "location":
            return self._validate_location_aoi()
        return self._validate_bbox_aoi()

    def _validate_bbox_aoi(self) -> "SearchSchema":
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

    def _validate_location_aoi(self) -> "SearchSchema":
        if self.aoi.lat is None or self.aoi.lon is None:
            raise ValueError("Location AOI requires both lat and lon.")
        if not (-90 <= self.aoi.lat <= 90):
            raise ValueError(
                f"lat ({self.aoi.lat}) is outside valid EPSG:4326 range [-90, 90]."
            )
        if not (-180 <= self.aoi.lon <= 180):
            raise ValueError(
                f"lon ({self.aoi.lon}) is outside valid EPSG:4326 range [-180, 180]."
            )
        radius = self.aoi.radius_km if self.aoi.radius_km is not None else 10.0
        if not (1 <= radius <= 100):
            raise ValueError(f"radius_km ({radius}) must be between 1 and 100 km.")
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
    def require_at_least_one_selection(self) -> "SearchSchema":
        """A search needs something to search for.

        Per-selection existence and date-window checks are the resolver's
        job (``core.search.utils.resolve_selections``), where an invalid
        selection is warned about and skipped instead of failing the whole
        search. This only guards the empty case.
        """
        if not self.selections:
            raise ValueError("At least one satellite selection is required.")
        return self
