"""Notification ports for the human-in-the-loop approval workflow (Stage 2)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from autoparkgpt.domain.entities.reservation import Reservation


@runtime_checkable
class AdminNotifierPort(Protocol):
    """Alerts an administrator that a reservation is awaiting review."""

    def notify_new_reservation(self, reservation: Reservation) -> None:
        """Send a new pending reservation to the administrator channel."""
        ...


@runtime_checkable
class UserNotifierPort(Protocol):
    """Informs the user of the administrator's decision on their reservation."""

    def notify_decision(self, reservation: Reservation) -> None:
        """Notify the user that their reservation was approved or rejected."""
        ...
