"""Saved query schema: a persisted search (params + results) under ~/.bhoonidhi/queries/."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .aoi import AOISchema


class QuerySchema(BaseModel):
    slug: str = Field(description="Unique slug identifier (adjective-noun)")
    name: str = Field(
        description="Human-readable name (auto-generated, user-overridable)"
    )
    description: str = Field(
        description="Human-readable description (auto-generated, user-overridable)"
    )
    created_at: datetime = Field(description="When this query was first created")
    satellite: str = Field(description="Satellite name")
    sensor: str | None = Field(default=None, description="Sensor name")
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
