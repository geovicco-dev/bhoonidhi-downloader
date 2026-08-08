from typing import Annotated

from pydantic import BaseModel, Field

from .scene import SceneSchema


class DownloadSchema(BaseModel):
    scene: Annotated[SceneSchema, "Scene ID"] = Field(default_factory=SceneSchema)
