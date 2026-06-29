"""Tests for the Stage 4 reservation-orchestration workflow (LangGraph + interrupt)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autoparkgpt.application.factory import build_reservation_workflow
from autoparkgpt.application.use_cases import ReservationWorkflow
from autoparkgpt.domain.entities.reservation import (
    Reservation,
    ReservationDraft,
    ReservationStatus,
)
from autoparkgpt.domain.exceptions import ReservationError
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod
from autoparkgpt.infrastructure.persistence import InMemoryReservationRepository
from tests.fakes import (
    RecordingAdminNotifier,
    RecordingReservationRecorder,
    RecordingUserNotifier,
)

_NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _reservation(start: datetime | None = None) -> Reservation:
    start = start or datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    ).to_reservation()


def _build() -> tuple[
    ReservationWorkflow,
    InMemoryReservationRepository,
    RecordingAdminNotifier,
    RecordingUserNotifier,
    RecordingReservationRecorder,
]:
    repo = InMemoryReservationRepository()
    admin = RecordingAdminNotifier()
    user = RecordingUserNotifier()
    recorder = RecordingReservationRecorder()
    workflow = build_reservation_workflow(
        reservation_repo=repo,
        admin_notifier=admin,
        user_notifier=user,
        recorder=recorder,
        max_reservation_days=30,
        clock=lambda: _NOW,
    )
    return workflow, repo, admin, user, recorder


def test_start_persists_pending_notifies_admin_and_pauses() -> None:
    workflow, repo, admin, user, recorder = _build()
    reservation = _reservation()

    workflow.start(reservation)

    assert repo.get(reservation.id).status is ReservationStatus.PENDING_APPROVAL
    assert [r.id for r in admin.notified] == [reservation.id]  # admin alerted
    assert workflow.is_pending(reservation.id)  # paused at the approval interrupt
    assert user.decisions == []  # user not yet notified
    assert recorder.recorded == []  # not recorded until approved


def test_resume_approve_records_and_notifies() -> None:
    workflow, repo, _admin, user, recorder = _build()
    reservation = _reservation()
    workflow.start(reservation)

    result = workflow.resume(reservation.id, "approve")

    assert result.status is ReservationStatus.APPROVED
    assert repo.get(reservation.id).status is ReservationStatus.APPROVED
    assert [r.id for r in recorder.recorded] == [reservation.id]  # MCP-communication node ran
    assert [r.id for r in user.decisions] == [reservation.id]
    assert not workflow.is_pending(reservation.id)  # run completed


def test_resume_reject_notifies_but_does_not_record() -> None:
    workflow, _repo, _admin, user, recorder = _build()
    reservation = _reservation()
    workflow.start(reservation)

    result = workflow.resume(reservation.id, "reject")

    assert result.status is ReservationStatus.REJECTED
    assert recorder.recorded == []  # not recorded on rejection
    assert [r.id for r in user.decisions] == [reservation.id]


def test_validation_error_routes_to_error_handler() -> None:
    workflow, repo, admin, _user, _recorder = _build()
    # Period in the past relative to the fixed clock -> validation fails.
    reservation = _reservation(start=datetime(2020, 1, 1, 9, 0, tzinfo=UTC))

    workflow.start(reservation)

    assert repo.get(reservation.id) is None  # never persisted
    assert admin.notified == []  # admin not notified
    assert not workflow.is_pending(reservation.id)  # ended at error_handler


def test_resume_without_run_raises() -> None:
    workflow, *_ = _build()
    with pytest.raises(ReservationError, match="No in-progress approval workflow"):
        workflow.resume("nonexistent-id", "approve")
