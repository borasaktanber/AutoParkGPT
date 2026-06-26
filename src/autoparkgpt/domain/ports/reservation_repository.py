"""Reservation repository port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from autoparkgpt.domain.entities.reservation import Reservation, ReservationStatus


@runtime_checkable
class ReservationRepositoryPort(Protocol):
    """Persistence abstraction for reservations."""

    def add(self, reservation: Reservation) -> Reservation:
        """Persist a new reservation and return the stored entity."""
        ...

    def update(self, reservation: Reservation) -> Reservation:
        """Persist changes to an existing reservation (e.g. a status transition)."""
        ...

    def get(self, reservation_id: str) -> Reservation | None:
        """Fetch a reservation by id, or ``None`` if not found."""
        ...

    def find_by_reference(self, reference: str) -> Reservation | None:
        """Fetch a reservation by a short reference (id prefix) or full id."""
        ...

    def list_all(self) -> list[Reservation]:
        """Return all reservations (most-recent first)."""
        ...

    def list_by_status(self, status: ReservationStatus) -> list[Reservation]:
        """Return reservations with the given status (most-recent first)."""
        ...
