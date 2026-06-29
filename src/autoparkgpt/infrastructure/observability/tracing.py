"""LangSmith tracing setup.

The LangChain/LangSmith client reads its configuration from the **process environment**
(``LANGSMITH_TRACING``, ``LANGSMITH_API_KEY``, ...). Our typed settings load these from
``.env`` via pydantic-settings, but pydantic does not export them back to ``os.environ`` —
so without this step the app process would never trace, even with the values in ``.env``.

``configure_tracing`` bridges that gap: it exports the resolved settings into the
environment (idempotently, never overriding values already set by the deployment) so the
LangChain runnables emit traces. Tracing is opt-in and fails closed — if it is disabled or
no API key is present, nothing is exported and no data leaves the process.
"""

from __future__ import annotations

import os

import structlog

from autoparkgpt.infrastructure.config.settings import ObservabilitySettings

_logger = structlog.get_logger(__name__)


def configure_tracing(settings: ObservabilitySettings) -> bool:
    """Export LangSmith env vars so LangChain emits traces. Returns whether enabled.

    No-op (and returns ``False``) unless tracing is switched on *and* an API key is
    present. Existing environment values win over ``.env`` so a deployment can override.
    """

    if not settings.tracing or settings.api_key is None:
        return False

    exported = {
        "LANGSMITH_TRACING": "true",
        "LANGCHAIN_TRACING_V2": "true",  # legacy alias still honored by some integrations
        "LANGSMITH_API_KEY": settings.api_key.get_secret_value(),
        "LANGSMITH_PROJECT": settings.project,
    }
    if settings.endpoint:
        exported["LANGSMITH_ENDPOINT"] = settings.endpoint

    for key, value in exported.items():
        os.environ.setdefault(key, value)

    _logger.info("langsmith_tracing_enabled", project=settings.project)
    return True
