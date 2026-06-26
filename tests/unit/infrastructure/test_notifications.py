"""Tests for notifier adapters and the selection factory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from autoparkgpt.domain.entities.reservation import ReservationDraft
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod
from autoparkgpt.infrastructure.config import AdminSettings
from autoparkgpt.infrastructure.notifications import (
    LoggingAdminNotifier,
    LoggingUserNotifier,
    WebhookAdminNotifier,
    WebhookUserNotifier,
    build_admin_notifier,
    build_user_notifier,
    reservation_payload,
)


def _reservation() -> object:
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    ).to_reservation()


def test_reservation_payload_is_json_safe() -> None:
    payload = reservation_payload(_reservation())
    assert payload["reference"] == payload["id"][:8]
    assert payload["car_number"] == "AB123CD"
    assert payload["status"] == "pending_approval"


def test_factory_defaults_to_logging() -> None:
    assert isinstance(build_admin_notifier(AdminSettings()), LoggingAdminNotifier)
    assert isinstance(build_user_notifier(AdminSettings()), LoggingUserNotifier)


def test_factory_selects_webhook_when_url_set() -> None:
    admin = build_admin_notifier(AdminSettings(admin_webhook_url="https://example.com/admin"))
    user = build_user_notifier(AdminSettings(user_webhook_url="https://example.com/user"))
    assert isinstance(admin, WebhookAdminNotifier)
    assert isinstance(user, WebhookUserNotifier)


def test_webhook_posts_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", fake_post)
    WebhookAdminNotifier("https://example.com/admin").notify_new_reservation(_reservation())
    assert captured["url"] == "https://example.com/admin"
    body = captured["json"]
    assert isinstance(body, dict)
    assert body["event"] == "reservation.pending"


def test_webhook_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    # Must not raise — notification failures cannot break the workflow.
    WebhookUserNotifier("https://example.com/user").notify_decision(_reservation())
