from pydantic import BaseModel, Field


class SceneSchema(BaseModel):
    id: str | None = Field(default=None, description="Scene ID")
    satellite: str | None = Field(default=None, description="Satellite Name")
    sensor: str | None = Field(default=None, description="Sensor Name")
    path: str | None = Field(default=None, description="Scene Path")
