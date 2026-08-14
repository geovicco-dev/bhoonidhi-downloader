from typing import Literal

from pydantic import BaseModel, Field


class AOISchema(BaseModel):
    name: str | None = Field(default=None, description="Name of the area of interest")
    mode: Literal["bbox", "location"] = Field(
        default="bbox", description="How this AOI is defined"
    )

    # bbox mode
    min_lon: float = Field(default=0.0, description="Minimum longitude")
    min_lat: float = Field(default=0.0, description="Minimum latitude")
    max_lon: float = Field(default=0.0, description="Maximum longitude")
    max_lat: float = Field(default=0.0, description="Maximum latitude")

    # location mode: a point plus a surrounding radius
    lat: float | None = Field(default=None, description="Point latitude")
    lon: float | None = Field(default=None, description="Point longitude")
    radius_km: float | None = Field(
        default=None, description="Search radius around the point, in km (1-100)"
    )
