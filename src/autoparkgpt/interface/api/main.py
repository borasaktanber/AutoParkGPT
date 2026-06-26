"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from autoparkgpt.application.use_cases import ChatService
from autoparkgpt.container import Container, build_container
from autoparkgpt.domain.exceptions import DomainError
from autoparkgpt.infrastructure.persistence import seed_dynamic_data
from autoparkgpt.interface.api.schemas import ChatReply, ChatRequest, HealthReply

_logger = structlog.get_logger(__name__)
_CHAT_PAGE = Path(__file__).parent / "static" / "chat.html"


def _get_chat_service(request: Request) -> ChatService:
    container: Container = request.app.state.container
    service: ChatService = container.chat_service()
    return service


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    settings = container.settings()

    # In tests, skip all external initialization (services aren't running).
    if settings.app.environment != "test":
        try:
            if settings.app.environment != "production":
                database = container.database()
                database.create_all()
                seed_dynamic_data(database)
            container.vector_store().ensure_schema()
        except Exception:  # pragma: no cover - best-effort startup, never crash boot
            _logger.warning("startup_init_failed", exc_info=True)
    yield


def create_app(container: Container | None = None) -> FastAPI:
    """Create the FastAPI application, optionally with an injected (test) container."""

    container = container or build_container()
    app = FastAPI(title="AutoParkGPT", version="0.1.0", lifespan=_lifespan)
    app.state.container = container

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        # Domain errors map to 400 with a safe message (no internals leaked).
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/", include_in_schema=False)
    def chat_ui() -> FileResponse:
        return FileResponse(_CHAT_PAGE)

    @app.get("/health", response_model=HealthReply)
    def health() -> HealthReply:
        settings = container.settings()
        return HealthReply(name=settings.app.name, environment=settings.app.environment)

    @app.post("/chat", response_model=ChatReply)
    def chat(
        payload: ChatRequest,
        service: ChatService = Depends(_get_chat_service),
    ) -> ChatReply:
        response = service.respond(payload.session_id, payload.message)
        return ChatReply.from_response(response)

    return app


# Module-level ASGI app for `uvicorn autoparkgpt.interface.api.main:app` and the Docker
# image CMD. Building it is cheap — DI providers are lazy and resolve on first request.
app = create_app()
