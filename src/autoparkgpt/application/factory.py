"""Assemble a ready-to-use :class:`ChatService` from domain ports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from autoparkgpt.application.graphs.chat_graph import build_chat_graph
from autoparkgpt.application.graphs.nodes import GraphNodes
from autoparkgpt.application.graphs.orchestration import (
    OrchestrationNodes,
    build_orchestration_graph,
)
from autoparkgpt.application.use_cases.chat_service import ChatService
from autoparkgpt.application.use_cases.reservation_workflow import ReservationWorkflow
from autoparkgpt.domain.ports.dynamic_data import DynamicDataPort
from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.guardrail import GuardrailPort
from autoparkgpt.domain.ports.llm import LLMPort
from autoparkgpt.domain.ports.notifications import AdminNotifierPort, UserNotifierPort
from autoparkgpt.domain.ports.reservation_recorder import ReservationRecorderPort
from autoparkgpt.domain.ports.reservation_repository import ReservationRepositoryPort
from autoparkgpt.domain.ports.vector_store import VectorStorePort
from autoparkgpt.infrastructure.config import AppSettings, RetrievalSettings


def build_chat_service(  # noqa: PLR0913 - wiring factory binds all ports + settings
    *,
    llm: LLMPort,
    embedding: EmbeddingPort,
    vector_store: VectorStorePort,
    dynamic_data: DynamicDataPort,
    guardrail: GuardrailPort,
    reservation_repo: ReservationRepositoryPort,
    admin_notifier: AdminNotifierPort,
    retrieval: RetrievalSettings,
    app: AppSettings,
    clock: Callable[[], datetime] | None = None,
    checkpointer: Any | None = None,
    workflow: ReservationWorkflow | None = None,
) -> ChatService:
    """Wire the graph nodes, compile the graph, and return a :class:`ChatService`."""

    nodes = GraphNodes(
        llm=llm,
        embedding=embedding,
        vector_store=vector_store,
        dynamic_data=dynamic_data,
        guardrail=guardrail,
        reservation_repo=reservation_repo,
        admin_notifier=admin_notifier,
        retrieval=retrieval,
        app=app,
        clock=clock or (lambda: datetime.now(UTC)),
        workflow=workflow,
    )
    graph = build_chat_graph(nodes, checkpointer=checkpointer or MemorySaver())
    return ChatService(graph)


def build_reservation_workflow(  # noqa: PLR0913 - wiring factory binds all ports + settings
    *,
    reservation_repo: ReservationRepositoryPort,
    admin_notifier: AdminNotifierPort,
    user_notifier: UserNotifierPort,
    recorder: ReservationRecorderPort,
    max_reservation_days: int,
    clock: Callable[[], datetime] | None = None,
    checkpointer: Any | None = None,
) -> ReservationWorkflow:
    """Wire the orchestration nodes, compile the graph, and return the workflow."""

    nodes = OrchestrationNodes(
        repo=reservation_repo,
        admin_notifier=admin_notifier,
        user_notifier=user_notifier,
        recorder=recorder,
        max_reservation_days=max_reservation_days,
        clock=clock or (lambda: datetime.now(UTC)),
    )
    graph = build_orchestration_graph(nodes, checkpointer=checkpointer or MemorySaver())
    return ReservationWorkflow(graph)
