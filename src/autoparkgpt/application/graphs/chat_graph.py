"""Assembles the conversation StateGraph.

Flow:
    START -> ingest_input -> (blocked?) -> output_guard -> END
                          \-> classify -> {retrieve | fetch_dynamic | reserve | generate}
    retrieve / fetch_dynamic -> generate -> output_guard -> END
    reserve -> output_guard -> END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from autoparkgpt.application.extraction import Intent
from autoparkgpt.application.graphs.nodes import GraphNodes
from autoparkgpt.application.graphs.state import ConversationState


def _route_after_input(state: ConversationState) -> str:
    return "blocked" if state.get("blocked") else "continue"


def _route_after_classify(state: ConversationState) -> str:
    return state.get("intent", Intent.INFO).value


def build_chat_graph(nodes: GraphNodes, checkpointer: Any | None = None) -> Any:
    """Build and compile the conversation graph.

    Args:
        nodes: the node implementations bound to domain ports.
        checkpointer: optional LangGraph checkpointer for per-session persistence.
    """

    graph = StateGraph(ConversationState)

    graph.add_node("ingest_input", nodes.ingest_input)
    graph.add_node("classify", nodes.classify)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("fetch_dynamic", nodes.fetch_dynamic)
    graph.add_node("reserve", nodes.reserve)
    graph.add_node("reservation_status", nodes.reservation_status)
    graph.add_node("generate", nodes.generate)
    graph.add_node("output_guard", nodes.output_guard)

    graph.add_edge(START, "ingest_input")
    graph.add_conditional_edges(
        "ingest_input",
        _route_after_input,
        {"blocked": "output_guard", "continue": "classify"},
    )
    graph.add_conditional_edges(
        "classify",
        _route_after_classify,
        {
            Intent.INFO.value: "retrieve",
            Intent.DYNAMIC.value: "fetch_dynamic",
            Intent.RESERVE.value: "reserve",
            Intent.STATUS.value: "reservation_status",
            Intent.OTHER.value: "generate",
        },
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("fetch_dynamic", "generate")
    graph.add_edge("generate", "output_guard")
    graph.add_edge("reserve", "output_guard")
    graph.add_edge("reservation_status", "output_guard")
    graph.add_edge("output_guard", END)

    return graph.compile(checkpointer=checkpointer)
