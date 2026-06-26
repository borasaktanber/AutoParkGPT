"""Tests for the ReservationPeriod value object."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autoparkgpt.domain.exceptions import InvalidReservationPeriodError
from autoparkgpt.domain.value_objects import ReservationPeriod


def _dt(**kw: int) -> datetime:
    base = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
    return base + timedelta(**kw)


def test_valid_period_has_duration() -> None:
    period = ReservationPeriod(start=_dt(), end=_dt(hours=3))
    assert period.duration == timedelta(hours=3)


def test_end_must_be_after_start() -> None:
    with pytest.raises(InvalidReservationPeriodError):
        ReservationPeriod(start=_dt(hours=2), end=_dt(hours=1))
    with pytest.raises(InvalidReservationPeriodError):
        ReservationPeriod(start=_dt(), end=_dt())


def test_validate_window_rejects_past_start() -> None:
    period = ReservationPeriod(start=_dt(), end=_dt(hours=1))
    future_now = _dt(days=1)
    with pytest.raises(InvalidReservationPeriodError):
        period.validate_window(now=future_now, max_days=30)


def test_validate_window_rejects_overlong_duration() -> None:
    period = ReservationPeriod(start=_dt(), end=_dt(days=40))
    with pytest.raises(InvalidReservationPeriodError):
        period.validate_window(now=_dt(hours=-1), max_days=30)


def test_validate_window_accepts_valid() -> None:
    period = ReservationPeriod(start=_dt(), end=_dt(days=2))
    period.validate_window(now=_dt(hours=-1), max_days=30)  # must not raise
