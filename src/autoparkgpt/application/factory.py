"""Assemble a ready-to-use :class:`ChatService` from domain ports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from autoparkgpt.application.graphs.chat_graph import build_chat_graph
from autoparkgpt.application.graphs.nodes import GraphNodes
from autoparkgpt.application.use_cases.chat_service import ChatService
from autoparkgpt.domain.ports.dynamic_data import DynamicDataPort
from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.guardrail import GuardrailPort
from autoparkgpt.domain.ports.llm import LLMPort
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
    retrieval: RetrievalSettings,
    app: AppSettings,
    clock: Callable[[], datetime] | None = None,
    checkpointer: Any | None = None,
) -> ChatService:
    """Wire the graph nodes, compile the graph, and return a :class:`ChatService`."""

    nodes = GraphNodes(
        llm=llm,
        embedding=embedding,
        vector_store=vector_store,
        dynamic_data=dynamic_data,
        guardrail=guardrail,
        reservation_repo=reservation_repo,
        retrieval=retrieval,
        app=app,
        clock=clock or (lambda: datetime.now(UTC)),
    )
    graph = build_chat_graph(nodes, checkpointer=checkpointer or MemorySaver())
    return ChatService(graph)
