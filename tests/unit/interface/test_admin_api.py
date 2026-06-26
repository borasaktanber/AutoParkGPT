"""Tests for the secured administrator REST endpoints (Stage 2)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from autoparkgpt.application.use_cases import AdminApprovalAgent, AdminApprovalService
from autoparkgpt.container import Container
from autoparkgpt.domain.entities.reservation import Reservation, ReservationDraft
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod
from autoparkgpt.infrastructure.config import AdminSettings, AppSettings, Settings
from autoparkgpt.infrastructure.persistence import InMemoryReservationRepository
from autoparkgpt.interface.api import create_app
from tests.fakes import FakeLLM, RecordingUserNotifier

_TOKEN = "secret-admin-token"  # test fixture value, not a real secret


def _reservation(first: str = "Ada") -> Reservation:
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationDraft(
        first_name=first,
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    ).to_reservation()


@pytest.fixture
def repo() -> InMemoryReservationRepository:
    return InMemoryReservationRepository()


@pytest.fixture
def client(repo: InMemoryReservationRepository) -> Iterator[TestClient]:
    container = Container()
    settings = Settings(app=AppSettings(environment="test"), admin=AdminSettings(api_token=_TOKEN))
    container.settings.override(providers.Object(settings))
    service = AdminApprovalService(repo, RecordingUserNotifier())
    container.approval_service.override(providers.Object(service))
    container.admin_agent.override(
        providers.Object(AdminApprovalAgent(FakeLLM(["APPROVE"]), service))
    )
    with TestClient(create_app(container)) as test_client:
        yield test_client


def _auth() -> dict[str, str]:
    return {"X-Admin-Token": _TOKEN}


def test_admin_ui_served_without_token(client: TestClient) -> None:
    # The console page is static (no secrets); it must load so the admin can enter a token.
    response = client.get("/admin/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Admin Console" in response.text


def test_requires_token(client: TestClient) -> None:
    assert client.get("/admin/reservations").status_code == 401


def test_rejects_wrong_token(client: TestClient) -> None:
    assert client.get("/admin/reservations", headers={"X-Admin-Token": "nope"}).status_code == 401


def test_list_pending(client: TestClient, repo: InMemoryReservationRepository) -> None:
    repo.add(_reservation("Ada"))
    repo.add(_reservation("Grace"))
    response = client.get("/admin/reservations", headers=_auth())
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {r["reference"] for r in body} == {r.id[:8] for r in repo.list_all()}


def test_approve(client: TestClient, repo: InMemoryReservationRepository) -> None:
    saved = repo.add(_reservation())
    response = client.post(f"/admin/reservations/{saved.id[:8]}/approve", headers=_auth())
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert repo.get(saved.id).status.value == "approved"


def test_reject(client: TestClient, repo: InMemoryReservationRepository) -> None:
    saved = repo.add(_reservation())
    response = client.post(f"/admin/reservations/{saved.id}/reject", headers=_auth())
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_decision_via_agent(client: TestClient, repo: InMemoryReservationRepository) -> None:
    saved = repo.add(_reservation())
    response = client.post(
        f"/admin/reservations/{saved.id[:8]}/decision",
        headers=_auth(),
        json={"instruction": "looks good, approve it"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_approve_unknown_reference(client: TestClient) -> None:
    response = client.post("/admin/reservations/deadbeef/approve", headers=_auth())
    assert response.status_code == 400  # DomainError -> 400
