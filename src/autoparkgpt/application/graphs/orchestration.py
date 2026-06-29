r"""Stage 4 — unified reservation-lifecycle orchestration (LangGraph).

A single resumable graph that ties the components together:

    validate -> persist_pending -> notify_admin -> human_approval (interrupt)
        -> apply_decision -> [approved] mcp_communication -> notify_user -> END
                          \-> [rejected] -------------------> notify_user -> END
    (any validation error) -> error_handler -> END

Human approval uses LangGraph's ``interrupt``: the run pauses after notifying the admin
and is resumed (via ``Command(resume=...)``) when the administrator decides. A checkpointer
persists the paused state between the two requests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from autoparkgpt.domain.entities.reservation import Reservation, ReservationStatus
from autoparkgpt.domain.exceptions import InvalidReservationPeriodError
from autoparkgpt.domain.ports.notifications import AdminNotifierPort, UserNotifierPort
from autoparkgpt.domain.ports.reservation_recorder import ReservationRecorderPort
from autoparkgpt.domain.ports.reservation_repository import ReservationRepositoryPort

_logger = structlog.get_logger(__name__)

_APPROVE = "approve"
_REJECT = "reject"


class WorkflowState(TypedDict, total=False):
    """Typed state threaded through the reservation-orchestration graph."""

    reservation: Reservation
    decision: str  # "approve" | "reject", supplied when the interrupt is resumed
    status: str
    recorded: bool
    error: str


@dataclass(slots=True)
class OrchestrationNodes:
    """Nodes for the reservation-lifecycle graph, bound to domain ports."""

    repo: ReservationRepositoryPort
    admin_notifier: AdminNotifierPort
    user_notifier: UserNotifierPort
    recorder: ReservationRecorderPort
    max_reservation_days: int
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def validate(self, state: WorkflowState) -> WorkflowState:
        reservation = state["reservation"]
        try:
            reservation.period.validate_window(
                now=self.clock(),
                max_days=self.max_reservation_days,
            )
        except InvalidReservationPeriodError as exc:
            return {"error": str(exc)}
        return {}

    def persist_pending(self, state: WorkflowState) -> WorkflowState:
        self.repo.add(state["reservation"])
        return {}

    def notify_admin(self, state: WorkflowState) -> WorkflowState:
        self.admin_notifier.notify_new_reservation(state["reservation"])
        return {}

    def human_approval(self, state: WorkflowState) -> WorkflowState:
        # Pause until an administrator resumes the run with "approve"/"reject".
        decision = interrupt(
            {
                "type": "approval_required",
                "reservation_id": state["reservation"].id,
                "reference": state["reservation"].id[:8],
            }
        )
        return {"decision": str(decision).strip().lower()}

    def apply_decision(self, state: WorkflowState) -> WorkflowState:
        reservation = state["reservation"]
        approved = state.get("decision") == _APPROVE
        updated = reservation.approve() if approved else reservation.reject()
        self.repo.update(updated)
        _logger.info(
            "orchestration_decision", reservation_id=updated.id, status=updated.status.value
        )
        return {"reservation": updated, "status": updated.status.value}

    def mcp_communication(self, state: WorkflowState) -> WorkflowState:
        # Persist the approved reservation through the recorder (MCP / file).
        self.recorder.record(state["reservation"])
        return {"recorded": True}

    def notify_user(self, state: WorkflowState) -> WorkflowState:
        self.user_notifier.notify_decision(state["reservation"])
        return {}

    def error_handler(self, state: WorkflowState) -> WorkflowState:
        _logger.warning("orchestration_error", error=state.get("error"))
        return {}


def _route_after_validate(state: WorkflowState) -> str:
    return "error" if state.get("error") else "ok"


def _route_after_decision(state: WorkflowState) -> str:
    return "approved" if state.get("status") == ReservationStatus.APPROVED.value else "rejected"


def build_orchestration_graph(nodes: OrchestrationNodes, checkpointer: Any) -> Any:
    """Build and compile the reservation-lifecycle graph (checkpointer required)."""

    graph = StateGraph(WorkflowState)
    graph.add_node("validate", nodes.validate)
    graph.add_node("persist_pending", nodes.persist_pending)
    graph.add_node("notify_admin", nodes.notify_admin)
    graph.add_node("human_approval", nodes.human_approval)
    graph.add_node("apply_decision", nodes.apply_decision)
    graph.add_node("mcp_communication", nodes.mcp_communication)
    graph.add_node("notify_user", nodes.notify_user)
    graph.add_node("error_handler", nodes.error_handler)

    graph.add_edge(START, "validate")
    graph.add_conditional_edges(
        "validate",
        _route_after_validate,
        {"ok": "persist_pending", "error": "error_handler"},
    )
    graph.add_edge("persist_pending", "notify_admin")
    graph.add_edge("notify_admin", "human_approval")
    graph.add_edge("human_approval", "apply_decision")
    graph.add_conditional_edges(
        "apply_decision",
        _route_after_decision,
        {"approved": "mcp_communication", "rejected": "notify_user"},
    )
    graph.add_edge("mcp_communication", "notify_user")
    graph.add_edge("notify_user", END)
    graph.add_edge("error_handler", END)

    return graph.compile(checkpointer=checkpointer)
