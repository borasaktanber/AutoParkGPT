"""Reservation entity, its lifecycle status, and the slot-filling draft."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autoparkgpt.domain.value_objects.car_number import CarNumber
from autoparkgpt.domain.value_objects.reservation_period import ReservationPeriod


class ReservationStatus(StrEnum):
    """Reservation lifecycle states.

    Stage 1 creates reservations in ``PENDING_APPROVAL``. The approve/reject transitions
    are exercised by the Stage 2 human-in-the-loop agent.
    """

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReservationSlot(StrEnum):
    """The fields collected interactively, in the order they are requested."""

    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    CAR_NUMBER = "car_number"
    PERIOD = "period"


# Canonical slot-filling order.
SLOT_ORDER: tuple[ReservationSlot, ...] = (
    ReservationSlot.FIRST_NAME,
    ReservationSlot.LAST_NAME,
    ReservationSlot.CAR_NUMBER,
    ReservationSlot.PERIOD,
)


class Reservation(BaseModel):
    """A completed, validated reservation request."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    car_number: CarNumber
    period: ReservationPeriod
    status: ReservationStatus = ReservationStatus.PENDING_APPROVAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def with_status(self, status: ReservationStatus) -> Reservation:
        """Return a copy with a new lifecycle status."""

        return self.model_copy(update={"status": status})


class ReservationDraft(BaseModel):
    """An immutable, partially-filled reservation collected during the conversation.

    Slots are filled one at a time; :meth:`updated` returns a new draft so the draft can
    live safely inside immutable LangGraph state.
    """

    model_config = ConfigDict(frozen=True)

    first_name: str | None = None
    last_name: str | None = None
    car_number: CarNumber | None = None
    period: ReservationPeriod | None = None

    def updated(self, **changes: object) -> ReservationDraft:
        """Return a new draft with the given fields replaced."""

        return self.model_copy(update=changes)

    def missing_slots(self) -> tuple[ReservationSlot, ...]:
        """Return the still-unfilled slots, in canonical request order."""

        values: dict[ReservationSlot, object | None] = {
            ReservationSlot.FIRST_NAME: self.first_name,
            ReservationSlot.LAST_NAME: self.last_name,
            ReservationSlot.CAR_NUMBER: self.car_number,
            ReservationSlot.PERIOD: self.period,
        }
        return tuple(slot for slot in SLOT_ORDER if values[slot] is None)

    @property
    def is_complete(self) -> bool:
        return not self.missing_slots()

    def to_reservation(self) -> Reservation:
        """Materialize a :class:`Reservation` from a complete draft.

        Raises:
            ValueError: if the draft is not complete (guarded by callers via
                :attr:`is_complete`).
        """

        if not self.is_complete:
            raise ValueError("Cannot build a reservation from an incomplete draft.")
        # The is_complete check guarantees these are non-None.
        assert self.first_name is not None
        assert self.last_name is not None
        assert self.car_number is not None
        assert self.period is not None
        return Reservation(
            first_name=self.first_name,
            last_name=self.last_name,
            car_number=self.car_number,
            period=self.period,
        )
