"""Tests for the LangGraph Studio graph factories (``studio.py``).

The factories build the compiled graphs from the DI container. Here the container is
replaced with fakes so the graphs are built without touching Claude, Weaviate, or the
embedding model — exercising the wiring and the ``lru_cache`` memoization in isolation.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from autoparkgpt.application.graphs import studio
from autoparkgpt.infrastructure.config import Settings
from autoparkgpt.infrastructure.persistence import InMemoryReservationRepository
from tests.fakes import (
    AllowAllGuardrail,
    FakeDynamicData,
    FakeEmbedding,
    FakeLLM,
    FakeVectorStore,
    RecordingAdminNotifier,
    RecordingReservationRecorder,
    RecordingUserNotifier,
)

_CHAT_NODES = {
    "ingest_input",
    "classify",
    "retrieve",
    "fetch_dynamic",
    "reserve",
    "reservation_status",
    "generate",
    "output_guard",
}
_ORCHESTRATION_NODES = {
    "validate",
    "persist_pending",
    "notify_admin",
    "human_approval",
    "apply_decision",
    "mcp_communication",
    "notify_user",
    "error_handler",
}


def _fake_container() -> MagicMock:
    container = MagicMock()
    container.settings.return_value = Settings()
    container.llm.return_value = FakeLLM()
    container.embedding.return_value = FakeEmbedding()
    container.vector_store.return_value = FakeVectorStore()
    container.dynamic_data.return_value = FakeDynamicData()
    container.guardrail.return_value = AllowAllGuardrail()
    container.reservation_repo.return_value = InMemoryReservationRepository()
    container.admin_notifier.return_value = RecordingAdminNotifier()
    container.user_notifier.return_value = RecordingUserNotifier()
    container.reservation_recorder.return_value = RecordingReservationRecorder()
    return container


@pytest.fixture(autouse=True)
def _patch_container(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Replace the DI container with fakes and reset the memoization so each test builds
    # against the fakes rather than a graph cached by a previous call (or a live run).
    monkeypatch.setattr(studio, "build_container", _fake_container)
    studio.make_graph.cache_clear()
    studio.make_orchestration_graph.cache_clear()
    yield
    studio.make_graph.cache_clear()
    studio.make_orchestration_graph.cache_clear()


def test_make_graph_builds_chat_graph() -> None:
    nodes = studio.make_graph().get_graph().nodes
    assert _CHAT_NODES.issubset(nodes)


def test_make_orchestration_graph_builds_orchestration_graph() -> None:
    nodes = studio.make_orchestration_graph().get_graph().nodes
    assert _ORCHESTRATION_NODES.issubset(nodes)


def test_factories_are_memoized() -> None:
    # The dev server re-invokes the factory per request; memoization avoids rebuilding
    # (and re-loading the embedding model) each time.
    assert studio.make_graph() is studio.make_graph()
    assert studio.make_orchestration_graph() is studio.make_orchestration_graph()
