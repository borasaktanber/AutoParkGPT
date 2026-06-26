"""API request/response schemas (kept separate from domain entities)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from autoparkgpt.application.dto.chat import ChatResponse
from autoparkgpt.domain.entities.reservation import Reservation


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


class ReservationView(BaseModel):
    """Administrator-facing view of a reservation."""

    id: str
    reference: str
    first_name: str
    last_name: str
    car_number: str
    period_start: str
    period_end: str
    status: str

    @classmethod
    def from_entity(cls, reservation: Reservation) -> ReservationView:
        return cls(
            id=reservation.id,
            reference=reservation.id[:8],
            first_name=reservation.first_name,
            last_name=reservation.last_name,
            car_number=reservation.car_number.value,
            period_start=reservation.period.start.isoformat(),
            period_end=reservation.period.end.isoformat(),
            status=reservation.status.value,
        )


class DecisionRequest(BaseModel):
    """Free-text administrator decision interpreted by the admin agent."""

    instruction: str = Field(min_length=1, description="e.g. 'approve' or 'looks good, reject'")
