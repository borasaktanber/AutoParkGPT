"""Reservation repository port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from autoparkgpt.domain.entities.reservation import Reservation


@runtime_checkable
class ReservationRepositoryPort(Protocol):
    """Persistence abstraction for reservations."""

    def add(self, reservation: Reservation) -> Reservation:
        """Persist a new reservation and return the stored entity."""
        ...

    def get(self, reservation_id: str) -> Reservation | None:
        """Fetch a reservation by id, or ``None`` if not found."""
        ...

    def list_all(self) -> list[Reservation]:
        """Return all reservations (most-recent first)."""
        ...
