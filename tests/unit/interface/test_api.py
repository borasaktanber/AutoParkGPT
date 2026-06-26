"""Tests for the FastAPI application using an injected test container."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from autoparkgpt.application.factory import build_chat_service
from autoparkgpt.container import Container
from autoparkgpt.infrastructure.config import AppSettings, RetrievalSettings, Settings
from autoparkgpt.infrastructure.persistence import InMemoryReservationRepository
from autoparkgpt.interface.api import create_app
from tests.fakes import (
    AllowAllGuardrail,
    FakeDynamicData,
    FakeEmbedding,
    FakeVectorStore,
    RecordingAdminNotifier,
)
from tests.unit.application.test_chat_graph import ScriptedLLM


@pytest.fixture
def client() -> Iterator[TestClient]:
    container = Container()
    container.settings.override(providers.Object(Settings(app=AppSettings(environment="test"))))
    service = build_chat_service(
        llm=ScriptedLLM(intent="OTHER", answer="Hello! How can I help with parking?"),
        embedding=FakeEmbedding(),
        vector_store=FakeVectorStore(),
        dynamic_data=FakeDynamicData(),
        guardrail=AllowAllGuardrail(),
        reservation_repo=InMemoryReservationRepository(),
        admin_notifier=RecordingAdminNotifier(),
        retrieval=RetrievalSettings(),
        app=AppSettings(environment="test"),
    )
    container.chat_service.override(providers.Object(service))
    with TestClient(create_app(container)) as test_client:
        yield test_client


def test_chat_ui_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AutoParkGPT" in response.text


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"


def test_chat_returns_reply(client: TestClient) -> None:
    response = client.post("/chat", json={"session_id": "s1", "message": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert "Hello" in body["message"]
    assert body["intent"] == "OTHER"
    assert body["blocked"] is False


def test_chat_validation_error(client: TestClient) -> None:
    # Missing required 'message' field -> 422 from FastAPI validation.
    response = client.post("/chat", json={"session_id": "s1"})
    assert response.status_code == 422
