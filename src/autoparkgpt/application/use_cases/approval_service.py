"""Administrator approval workflow (Stage 2 human-in-the-loop)."""

from __future__ import annotations

import structlog

from autoparkgpt.application.prompts import ADMIN_DECISION_PROMPT
from autoparkgpt.application.use_cases.reservation_workflow import ReservationWorkflow
from autoparkgpt.domain.entities.reservation import Reservation, ReservationStatus
from autoparkgpt.domain.exceptions import ReservationError
from autoparkgpt.domain.ports.llm import LLMPort
from autoparkgpt.domain.ports.notifications import UserNotifierPort
from autoparkgpt.domain.ports.reservation_recorder import ReservationRecorderPort
from autoparkgpt.domain.ports.reservation_repository import ReservationRepositoryPort
from autoparkgpt.domain.value_objects.chat import ChatMessage

_logger = structlog.get_logger(__name__)


class AdminApprovalService:
    """Applies an administrator's decision to a reservation and notifies the user.

    This is the core of the second (administrator) agent: it transitions a pending
    reservation to approved/rejected, persists the change, and pushes the decision back
    toward the user — closing the human-in-the-loop with the first (chat) agent, which
    reads the updated status from the shared repository.
    """

    def __init__(
        self,
        reservation_repo: ReservationRepositoryPort,
        user_notifier: UserNotifierPort,
        recorder: ReservationRecorderPort | None = None,
        workflow: ReservationWorkflow | None = None,
    ) -> None:
        self._repo = reservation_repo
        self._notifier = user_notifier
        self._recorder = recorder
        self._workflow = workflow

    def list_pending(self) -> list[Reservation]:
        return self._repo.list_by_status(ReservationStatus.PENDING_APPROVAL)

    def list_all(self) -> list[Reservation]:
        """Return the full reservation history (most-recent first)."""

        return self._repo.list_all()

    def approve(self, reference: str) -> Reservation:
        return self._decide(reference, approve=True)

    def reject(self, reference: str) -> Reservation:
        return self._decide(reference, approve=False)

    def _decide(self, reference: str, *, approve: bool) -> Reservation:
        reservation = self._repo.find_by_reference(reference)
        if reservation is None:
            raise ReservationError(f"No reservation found for reference '{reference}'.")
        # Stage 4: if an orchestration run is awaiting approval, drive it (the graph
        # applies the decision, records via MCP, and notifies the user).
        if self._workflow is not None and self._workflow.is_pending(reservation.id):
            return self._workflow.resume(reservation.id, "approve" if approve else "reject")
        updated = reservation.approve() if approve else reservation.reject()
        self._repo.update(updated)
        self._notifier.notify_decision(updated)
        # On approval, record the reservation to the durable file (Stage 3 / MCP).
        # Best-effort: a recording failure must not roll back an approval already made.
        if approve and self._recorder is not None:
            try:
                self._recorder.record(updated)
            except Exception:  # pragma: no cover - defensive
                _logger.warning(
                    "reservation_record_failed", reservation_id=updated.id, exc_info=True
                )
        _logger.info(
            "reservation_decided",
            reservation_id=updated.id,
            status=updated.status.value,
        )
        return updated


class AdminApprovalAgent:
    """LLM-backed administrator agent that interprets a free-text decision.

    Wraps :class:`AdminApprovalService` so an administrator can write a natural-language
    instruction ("looks good, approve it") and have it mapped to an approve/reject action.
    """

    def __init__(self, llm: LLMPort, service: AdminApprovalService) -> None:
        self._llm = llm
        self._service = service

    def decide(self, reference: str, instruction: str) -> Reservation:
        verdict = self._interpret(instruction)
        if verdict == "approve":
            return self._service.approve(reference)
        if verdict == "reject":
            return self._service.reject(reference)
        raise ReservationError(
            "Could not interpret the decision. Please reply with 'approve' or 'reject'.",
        )

    def _interpret(self, instruction: str) -> str:
        prompt = ADMIN_DECISION_PROMPT.format(instruction=instruction)
        raw = self._llm.generate([ChatMessage.user(prompt)]).strip().upper()
        if "APPROVE" in raw:
            return "approve"
        if "REJECT" in raw:
            return "reject"
        return "unclear"
