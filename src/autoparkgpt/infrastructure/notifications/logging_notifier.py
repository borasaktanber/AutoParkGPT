"""Logging notifiers — the default channel for local/dev (no external endpoint)."""

from __future__ import annotations

import structlog

from autoparkgpt.domain.entities.reservation import Reservation

_logger = structlog.get_logger(__name__)


class LoggingAdminNotifier:
    """Logs new pending reservations instead of calling an external admin channel."""

    def notify_new_reservation(self, reservation: Reservation) -> None:
        _logger.info(
            "admin_notification.new_reservation",
            reservation_id=reservation.id,
            car_number=reservation.car_number.value,
            status=reservation.status.value,
        )


class LoggingUserNotifier:
    """Logs the administrator's decision instead of pushing it to the user."""

    def notify_decision(self, reservation: Reservation) -> None:
        _logger.info(
            "user_notification.decision",
            reservation_id=reservation.id,
            status=reservation.status.value,
        )
