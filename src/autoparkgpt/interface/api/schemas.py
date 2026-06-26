"""API request/response schemas (kept separate from domain entities)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from autoparkgpt.application.dto.chat import ChatResponse


class ChatRequest(BaseModel):
    """Incoming chat request."""

    session_id: str = Field(min_length=1, max_length=128, description="Conversation/session id")
    message: str = Field(min_length=1, description="User message")


class ChatReply(BaseModel):
    """Outgoing chat reply."""

    message: str
    intent: str | None = None
    sources: list[str] = Field(default_factory=list)
    reservation_id: str | None = None
    blocked: bool = False

    @classmethod
    def from_response(cls, response: ChatResponse) -> ChatReply:
        return cls(
            message=response.message,
            intent=response.intent,
            sources=response.sources,
            reservation_id=response.reservation_id,
            blocked=response.blocked,
        )


class HealthReply(BaseModel):
    """Health-check payload."""

    status: str = "ok"
    name: str
    environment: str
