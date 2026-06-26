"""Chat response DTO returned by the application layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatResponse(BaseModel):
    """The result of processing one user turn."""

    model_config = ConfigDict(frozen=True)

    message: str
    intent: str | None = None
    sources: list[str] = Field(default_factory=list)
    reservation_id: str | None = None
    blocked: bool = False
