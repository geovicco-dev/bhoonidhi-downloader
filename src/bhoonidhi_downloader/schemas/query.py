"""Saved query schema: a persisted search (params + results) under ~/.bhoonidhi/queries/."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .aoi import AOISchema
from .selection import Selection


class QuerySchema(BaseModel):
    slug: str = Field(description="Unique slug identifier (adjective-noun)")
    name: str = Field(
        description="Human-readable name (auto-generated, user-overridable)"
    )
    description: str = Field(
        description="Human-readable description (auto-generated, user-overridable)"
    )
    created_at: datetime = Field(description="When this query was first created")
    selections: list[Selection] = Field(
        description="Satellite/sensor/product targets this query searches"
    )
    aoi: AOISchema = Field(
        description="Area of interest \u2014 fixed for the lifetime of the query"
    )
    start_date: datetime = Field(description="Fixed start of the search window")
    end_date: datetime = Field(
        description="Data confirmed current through this date; advances on refresh"
    )
    scenes: list[dict[str, Any]] = Field(
        default_factory=list, description="Cached scene results"
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_scalar_satellite(cls, data: Any) -> Any:
        """Load pre-multi-selection saved queries.

        Queries saved before this feature carried scalar ``satellite`` and
        optional ``sensor`` fields instead of ``selections``. Fold those
        into a single-element ``selections`` list on read so existing saved
        queries keep working without a manual migration.
        """
        if isinstance(data, dict) and "selections" not in data and "satellite" in data:
            data = {**data}
            satellite = data.pop("satellite")
            sensor = data.pop("sensor", None)
            data["selections"] = [{"satellite": satellite, "sensor": sensor}]
        return data
