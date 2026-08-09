from pydantic import BaseModel, Field


class AOISchema(BaseModel):
    name: str | None = Field(default=None, description="Name of the area of interest")
    min_lon: float = Field(default=0.0, description="Minimum longitude")
    min_lat: float = Field(default=0.0, description="Minimum latitude")
    max_lon: float = Field(default=0.0, description="Maximum longitude")
    max_lat: float = Field(default=0.0, description="Maximum latitude")
