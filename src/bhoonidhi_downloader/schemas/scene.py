from typing import Annotated

from pydantic import BaseModel


class SceneSchema(BaseModel):
    id: Annotated[str, "Scene ID"] = None
    satellite: Annotated["str", "Satellite Name"] = None
    sensor: Annotated["str", "Sensor Name"] = None
    path: Annotated["str", "Scene Path"] = None
