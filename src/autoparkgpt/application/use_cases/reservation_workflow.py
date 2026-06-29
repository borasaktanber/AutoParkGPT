"""Reservation lifecycle workflow — drives the orchestration graph (Stage 4)."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from autoparkgpt.domain.entities.reservation import Reservation
from autoparkgpt.domain.exceptions import ReservationError


class ReservationWorkflow:
    """Starts and resumes the unified reservation-orchestration graph.

    ``start`` runs validation, persistence, and admin notification, then pauses at the
    human-approval interrupt. ``resume`` feeds the administrator's decision back in and
    runs the rest of the lifecycle (apply decision -> MCP record -> notify user).

    The graph's checkpointer persists the paused run keyed by the reservation id, so the
    two calls can come from different requests (chat creation, then admin decision).
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    def start(self, reservation: Reservation) -> Reservation:
        """Run up to the approval interrupt; returns the (pending) reservation."""

        config = {"configurable": {"thread_id": reservation.id}}
        self._graph.invoke({"reservation": reservation}, config=config)
        return reservation

    def resume(self, reservation_id: str, decision: str) -> Reservation:
        """Resume a paused run with the administrator's decision and finish the lifecycle."""

        if not self.is_pending(reservation_id):
            raise ReservationError(
                f"No in-progress approval workflow for reservation '{reservation_id}'."
            )
        config = {"configurable": {"thread_id": reservation_id}}
        result: dict[str, Any] = self._graph.invoke(Command(resume=decision), config=config)
        reservation = result.get("reservation")
        if not isinstance(reservation, Reservation):  # pragma: no cover - defensive
            raise ReservationError(
                f"No in-progress approval workflow for reservation '{reservation_id}'."
            )
        return reservation

    def is_pending(self, reservation_id: str) -> bool:
        """Whether a paused (awaiting-approval) run exists for this reservation."""

        config = {"configurable": {"thread_id": reservation_id}}
        snapshot = self._graph.get_state(config)
        return bool(getattr(snapshot, "next", ()))
