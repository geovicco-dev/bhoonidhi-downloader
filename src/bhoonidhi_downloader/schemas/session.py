from typing import Any

from pydantic import BaseModel


class SessionSchema(BaseModel):
    jwt: str | None = None
    userId: str | None = None
    user_email: str | None = None
    username: str | None = None
    password: str | None = None
    sid: str | None = None
    scenes: list[dict[str, Any]] = []
