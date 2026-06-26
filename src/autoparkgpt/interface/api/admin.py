"""Administrator REST endpoints (Stage 2 human-in-the-loop approval).

Secured by a shared admin token (``X-Admin-Token`` header) compared in constant time.
When no token is configured the endpoints fail closed (401), so the admin surface is
never unintentionally open.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from autoparkgpt.application.use_cases import AdminApprovalAgent, AdminApprovalService
from autoparkgpt.interface.api.schemas import DecisionRequest, ReservationView


def _require_admin(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """Authorize an admin request via the configured shared token (fail-closed)."""

    configured = request.app.state.container.settings().admin.api_token
    if configured is None or x_admin_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator access is not authorized.",
        )
    if not secrets.compare_digest(x_admin_token, configured.get_secret_value()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator access is not authorized.",
        )


def _service(request: Request) -> AdminApprovalService:
    service: AdminApprovalService = request.app.state.container.approval_service()
    return service


def _agent(request: Request) -> AdminApprovalAgent:
    agent: AdminApprovalAgent = request.app.state.container.admin_agent()
    return agent


def build_admin_router() -> APIRouter:
    """Build the `/admin` router (all routes require a valid admin token)."""

    router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(_require_admin)])

    @router.get("/reservations", response_model=list[ReservationView])
    def list_pending(service: AdminApprovalService = Depends(_service)) -> list[ReservationView]:
        return [ReservationView.from_entity(r) for r in service.list_pending()]

    @router.get("/history", response_model=list[ReservationView])
    def list_history(service: AdminApprovalService = Depends(_service)) -> list[ReservationView]:
        return [ReservationView.from_entity(r) for r in service.list_all()]

    @router.post("/reservations/{reference}/approve", response_model=ReservationView)
    def approve(
        reference: str,
        service: AdminApprovalService = Depends(_service),
    ) -> ReservationView:
        return ReservationView.from_entity(service.approve(reference))

    @router.post("/reservations/{reference}/reject", response_model=ReservationView)
    def reject(
        reference: str,
        service: AdminApprovalService = Depends(_service),
    ) -> ReservationView:
        return ReservationView.from_entity(service.reject(reference))

    @router.post("/reservations/{reference}/decision", response_model=ReservationView)
    def decide(
        reference: str,
        payload: DecisionRequest,
        agent: AdminApprovalAgent = Depends(_agent),
    ) -> ReservationView:
        # The admin agent interprets a natural-language instruction into approve/reject.
        return ReservationView.from_entity(agent.decide(reference, payload.instruction))

    return router
