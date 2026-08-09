from pydantic import BaseModel, Field

from .scene import SceneSchema


class DownloadSchema(BaseModel):
    scene: SceneSchema = Field(default_factory=SceneSchema, description="Scene ID")
