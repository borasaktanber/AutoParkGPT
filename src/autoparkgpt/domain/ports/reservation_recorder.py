"""Reservation recorder port (Stage 3 — write approved reservations to a file/MCP sink)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from autoparkgpt.domain.entities.reservation import Reservation


@runtime_checkable
class ReservationRecorderPort(Protocol):
    """Persists an approved reservation to the external record (a text file via MCP)."""

    def record(self, reservation: Reservation) -> None:
        """Append the approved reservation to the durable record."""
        ...
