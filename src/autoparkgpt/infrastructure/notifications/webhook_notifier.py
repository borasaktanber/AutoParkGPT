"""Webhook notifiers — POST reservation events to a configured HTTPS endpoint.

Delivery is best-effort: a failed webhook is logged but never propagated, so a
notification outage cannot block reservation creation or an admin decision.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from autoparkgpt.domain.entities.reservation import Reservation

_logger = structlog.get_logger(__name__)


def reservation_payload(reservation: Reservation) -> dict[str, Any]:
    """Serialize a reservation to a JSON-safe webhook payload."""

    return {
        "id": reservation.id,
        "reference": reservation.id[:8],
        "first_name": reservation.first_name,
        "last_name": reservation.last_name,
        "car_number": reservation.car_number.value,
        "period_start": reservation.period.start.isoformat(),
        "period_end": reservation.period.end.isoformat(),
        "status": reservation.status.value,
        "created_at": reservation.created_at.isoformat(),
    }


def _post(url: str, event: str, reservation: Reservation, timeout: float) -> None:
    payload = {"event": event, "reservation": reservation_payload(reservation)}
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.HTTPError:
        # NB: 'event' is reserved by structlog for the log message — use a distinct key.
        _logger.warning(
            "webhook_delivery_failed",
            notification_event=event,
            reservation_id=reservation.id,
            exc_info=True,
        )
        return
    if response.is_error:
        _logger.warning(
            "webhook_non_2xx",
            notification_event=event,
            reservation_id=reservation.id,
            status_code=response.status_code,
        )


class WebhookAdminNotifier:
    """Notifies an administrator endpoint of a new pending reservation."""

    def __init__(self, url: str, timeout: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout

    def notify_new_reservation(self, reservation: Reservation) -> None:
        _post(self._url, "reservation.pending", reservation, self._timeout)


class WebhookUserNotifier:
    """Notifies a user-callback endpoint of the administrator's decision."""

    def __init__(self, url: str, timeout: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout

    def notify_decision(self, reservation: Reservation) -> None:
        _post(self._url, f"reservation.{reservation.status.value}", reservation, self._timeout)
