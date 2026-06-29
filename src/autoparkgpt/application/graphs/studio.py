"""LangGraph Studio entry point.

Exposes a graph factory for `langgraph dev` / LangGraph Studio. The compiled graph is
built from the real DI container (so Studio talks to the live Claude, Weaviate, and SQL
backends configured in ``.env``). No application checkpointer is attached — the LangGraph
dev server supplies its own persistence.

Run:
    langgraph dev
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from autoparkgpt.application.graphs.chat_graph import build_chat_graph
from autoparkgpt.application.graphs.nodes import GraphNodes
from autoparkgpt.application.graphs.orchestration import (
    OrchestrationNodes,
    build_orchestration_graph,
)
from autoparkgpt.container import build_container


def make_graph() -> Any:
    """Build the compiled conversation graph for LangGraph Studio."""

    container = build_container()
    settings = container.settings()
    nodes = GraphNodes(
        llm=container.llm(),
        embedding=container.embedding(),
        vector_store=container.vector_store(),
        dynamic_data=container.dynamic_data(),
        guardrail=container.guardrail(),
        reservation_repo=container.reservation_repo(),
        admin_notifier=container.admin_notifier(),
        retrieval=settings.retrieval,
        app=settings.app,
    )
    return build_chat_graph(nodes, checkpointer=None)


def make_orchestration_graph() -> Any:
    """Build the compiled reservation-orchestration graph for LangGraph Studio.

    Studio can visualize the lifecycle and drive the human-approval ``interrupt``
    (resume the paused run with ``"approve"`` / ``"reject"``).
    """

    container = build_container()
    settings = container.settings()
    nodes = OrchestrationNodes(
        repo=container.reservation_repo(),
        admin_notifier=container.admin_notifier(),
        user_notifier=container.user_notifier(),
        recorder=container.reservation_recorder(),
        max_reservation_days=settings.app.max_reservation_days,
    )
    return build_orchestration_graph(nodes, checkpointer=MemorySaver())
