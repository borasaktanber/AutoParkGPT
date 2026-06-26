"""High-level chat use case wrapping the compiled conversation graph."""

from __future__ import annotations

from typing import Any

from autoparkgpt.application.dto.chat import ChatResponse
from autoparkgpt.application.extraction import Intent


class ChatService:
    """Processes a user turn through the LangGraph workflow.

    Session state (conversation history and the in-progress reservation draft) is keyed
    by ``session_id`` via the graph's checkpointer.
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    def respond(self, session_id: str, message: str) -> ChatResponse:
        config = {"configurable": {"thread_id": session_id}}
        result: dict[str, Any] = self._graph.invoke({"user_input": message}, config=config)

        blocked = bool(result.get("blocked", False))
        intent = result.get("intent")
        return ChatResponse(
            message=result.get("response", ""),
            # A blocked turn never reaches classification, so it has no meaningful intent
            # (guard against a stale value persisted from an earlier turn).
            intent=None if blocked else (intent.value if isinstance(intent, Intent) else None),
            sources=result.get("sources", []),
            reservation_id=result.get("reservation_id"),
            blocked=blocked,
        )
