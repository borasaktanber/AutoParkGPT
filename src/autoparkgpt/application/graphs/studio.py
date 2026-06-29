"""LangGraph Studio entry point.

Exposes a graph factory for `langgraph dev` / LangGraph Studio. The compiled graph is
built from the real DI container (so Studio talks to the live Claude, Weaviate, and SQL
backends configured in ``.env``). No application checkpointer is attached to the chat
graph — the LangGraph dev server supplies its own persistence.

Both factories are memoized with ``lru_cache``. The dev server re-invokes the factory on
every request that needs the graph (e.g. ``GET /assistants/{id}/graph`` for the Studio
preview); building it lazily each time would re-load the HuggingFace embedding model,
whose blocking filesystem calls trip the dev server's event-loop "blockbuster" guard and
fail the request. Building once and reusing keeps the factory non-blocking and fast.

Run:
    langgraph dev
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from autoparkgpt.application.graphs.chat_graph import build_chat_graph
from autoparkgpt.application.graphs.nodes import GraphNodes
from autoparkgpt.application.graphs.orchestration import (
    OrchestrationNodes,
    build_orchestration_graph,
)
from autoparkgpt.container import build_container


@lru_cache(maxsize=1)
def make_graph() -> Any:
    """Build (once) the compiled conversation graph for LangGraph Studio."""

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


@lru_cache(maxsize=1)
def make_orchestration_graph() -> Any:
    """Build (once) the compiled reservation-orchestration graph for LangGraph Studio.

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
