"""Domain entities."""

from autoparkgpt.domain.entities.reservation import (
    SLOT_ORDER,
    Reservation,
    ReservationDraft,
    ReservationSlot,
    ReservationStatus,
)

__all__ = [
    "SLOT_ORDER",
    "Reservation",
    "ReservationDraft",
    "ReservationSlot",
    "ReservationStatus",
]
