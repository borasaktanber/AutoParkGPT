"""Tests for the Reservation entity, draft, and slot-filling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autoparkgpt.domain.entities import (
    Reservation,
    ReservationDraft,
    ReservationSlot,
    ReservationStatus,
)
from autoparkgpt.domain.exceptions import ReservationError
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod


def _period() -> ReservationPeriod:
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationPeriod(start=start, end=start + timedelta(hours=4))


def test_empty_draft_missing_all_slots_in_order() -> None:
    draft = ReservationDraft()
    assert draft.missing_slots() == (
        ReservationSlot.FIRST_NAME,
        ReservationSlot.LAST_NAME,
        ReservationSlot.CAR_NUMBER,
        ReservationSlot.PERIOD,
    )
    assert not draft.is_complete


def test_updated_returns_new_draft_progressively() -> None:
    draft = ReservationDraft()
    draft2 = draft.updated(first_name="Ada")
    assert draft.first_name is None  # original untouched (immutable)
    assert draft2.first_name == "Ada"
    assert draft2.missing_slots()[0] == ReservationSlot.LAST_NAME


def test_complete_draft_builds_reservation() -> None:
    draft = ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=_period(),
    )
    assert draft.is_complete
    reservation = draft.to_reservation()
    assert isinstance(reservation, Reservation)
    assert reservation.first_name == "Ada"
    assert reservation.status is ReservationStatus.PENDING_APPROVAL
    assert reservation.id


def test_incomplete_draft_cannot_build() -> None:
    draft = ReservationDraft(first_name="Ada")
    with pytest.raises(ValueError, match="incomplete draft"):
        draft.to_reservation()


def test_approve_and_reject_transitions() -> None:
    draft = ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=_period(),
    )
    reservation = draft.to_reservation()
    assert reservation.approve().status is ReservationStatus.APPROVED
    assert reservation.reject().status is ReservationStatus.REJECTED


def test_cannot_decide_non_pending_reservation() -> None:
    draft = ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=_period(),
    )
    approved = draft.to_reservation().approve()
    with pytest.raises(ReservationError, match="not pending"):
        approved.approve()
    with pytest.raises(ReservationError, match="not pending"):
        approved.reject()


def test_with_status_returns_copy() -> None:
    draft = ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=_period(),
    )
    reservation = draft.to_reservation()
    approved = reservation.with_status(ReservationStatus.APPROVED)
    assert reservation.status is ReservationStatus.PENDING_APPROVAL
    assert approved.status is ReservationStatus.APPROVED
    assert approved.id == reservation.id
