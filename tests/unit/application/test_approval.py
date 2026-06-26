"""Tests for the Stage 2 admin approval service and LLM admin agent."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autoparkgpt.application.use_cases import AdminApprovalAgent, AdminApprovalService
from autoparkgpt.domain.entities.reservation import (
    Reservation,
    ReservationDraft,
    ReservationStatus,
)
from autoparkgpt.domain.exceptions import ReservationError
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod
from autoparkgpt.infrastructure.persistence import InMemoryReservationRepository
from tests.fakes import FakeLLM, RecordingReservationRecorder, RecordingUserNotifier


def _reservation(first: str = "Ada") -> Reservation:
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationDraft(
        first_name=first,
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    ).to_reservation()


def _service() -> tuple[AdminApprovalService, InMemoryReservationRepository, RecordingUserNotifier]:
    repo = InMemoryReservationRepository()
    notifier = RecordingUserNotifier()
    return AdminApprovalService(repo, notifier), repo, notifier


def test_list_pending() -> None:
    service, repo, _ = _service()
    repo.add(_reservation("Ada"))
    repo.add(_reservation("Grace"))
    assert len(service.list_pending()) == 2


def test_approve_updates_status_and_notifies_user() -> None:
    service, repo, notifier = _service()
    saved = repo.add(_reservation())
    updated = service.approve(saved.id[:8])  # approve by short reference
    assert updated.status is ReservationStatus.APPROVED
    assert repo.get(saved.id).status is ReservationStatus.APPROVED  # persisted
    assert notifier.decisions[-1].id == saved.id
    assert service.list_pending() == []  # no longer pending


def test_reject_updates_status_and_notifies() -> None:
    service, repo, notifier = _service()
    saved = repo.add(_reservation())
    updated = service.reject(saved.id)
    assert updated.status is ReservationStatus.REJECTED
    assert notifier.decisions[-1].status is ReservationStatus.REJECTED


def test_decide_unknown_reference_raises() -> None:
    service, _, _ = _service()
    with pytest.raises(ReservationError, match="No reservation found"):
        service.approve("deadbeef")


def test_approve_records_reservation_reject_does_not() -> None:
    repo = InMemoryReservationRepository()
    recorder = RecordingReservationRecorder()
    service = AdminApprovalService(repo, RecordingUserNotifier(), recorder=recorder)

    approved = repo.add(_reservation("Ada"))
    service.approve(approved.id[:8])
    assert [r.id for r in recorder.recorded] == [approved.id]  # recorded on approve

    rejected = repo.add(_reservation("Grace"))
    service.reject(rejected.id[:8])
    assert rejected.id not in [r.id for r in recorder.recorded]  # not recorded on reject


def test_admin_agent_interprets_natural_language() -> None:
    service, repo, _ = _service()
    saved = repo.add(_reservation())
    agent = AdminApprovalAgent(FakeLLM(["APPROVE"]), service)
    updated = agent.decide(saved.id[:8], "looks good, approve it")
    assert updated.status is ReservationStatus.APPROVED


def test_admin_agent_rejects() -> None:
    service, repo, _ = _service()
    saved = repo.add(_reservation())
    agent = AdminApprovalAgent(FakeLLM(["REJECT"]), service)
    assert agent.decide(saved.id, "no, deny this one").status is ReservationStatus.REJECTED


def test_admin_agent_unclear_raises() -> None:
    service, repo, _ = _service()
    saved = repo.add(_reservation())
    agent = AdminApprovalAgent(FakeLLM(["UNCLEAR"]), service)
    with pytest.raises(ReservationError, match=r"approve.*reject"):
        agent.decide(saved.id, "hmm what is this")
