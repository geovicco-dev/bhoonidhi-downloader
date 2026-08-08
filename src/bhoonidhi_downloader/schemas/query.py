"""Saved query schema: a persisted search (params + results) under ~/.bhoonidhi/queries/."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field

from .aoi import AOISchema


class QuerySchema(BaseModel):
    slug: Annotated[str, "Unique slug identifier (adjective-noun)"]
    name: Annotated[str, "Human-readable name (auto-generated, user-overridable)"]
    description: Annotated[
        str, "Human-readable description (auto-generated, user-overridable)"
    ]
    created_at: Annotated[datetime, "When this query was first created"]
    satellite: Annotated[str, "Satellite name"]
    sensor: Annotated[str | None, "Sensor name"] = None
    aoi: Annotated[
        AOISchema, "Area of interest \u2014 fixed for the lifetime of the query"
    ]
    start_date: Annotated[datetime, "Fixed start of the search window"]
    end_date: Annotated[
        datetime, "Data confirmed current through this date; advances on refresh"
    ]
    scenes: Annotated[list[dict[str, Any]], "Cached scene results"] = Field(
        default_factory=list
    )
