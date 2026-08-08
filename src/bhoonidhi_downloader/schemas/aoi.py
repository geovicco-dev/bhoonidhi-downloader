from typing import Annotated

from pydantic import BaseModel, Field


class AOISchema(BaseModel):
    name: Annotated[str | None, "Name of the area of interest"] = None
    min_lon: Annotated[float, "Minimum longitude"] = Field(default=0.0)
    min_lat: Annotated[float, "Minimum latitude"] = Field(default=0.0)
    max_lon: Annotated[float, "Maximum longitude"] = Field(default=0.0)
    max_lat: Annotated[float, "Maximum latitude"] = Field(default=0.0)
