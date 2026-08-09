from typing import Any

from pydantic import BaseModel, Field


class SessionSchema(BaseModel):
    jwt: str | None = Field(default=None, description="Bhoonidhi session JWT")
    userId: str | None = Field(default=None, description="Bhoonidhi user ID")
    user_email: str | None = Field(default=None, description="Account email")
    username: str | None = Field(default=None, description="Bhoonidhi username")
    password: str | None = Field(default=None, description="Bhoonidhi password")
    sid: str | None = Field(default=None, description="Session ID")
    scenes: list[dict[str, Any]] = Field(
        default_factory=list, description="Scenes attached to this session"
    )
