"""Unit tests for the DI composition root."""

from __future__ import annotations

from autoparkgpt.container import build_container
from autoparkgpt.infrastructure.config import Settings


def test_container_provides_settings() -> None:
    container = build_container()
    settings = container.settings()
    assert isinstance(settings, Settings)
    container.shutdown_resources()


def test_container_initializes_logging_without_error() -> None:
    # build_container() initializes the logging resource as a side effect.
    container = build_container()
    container.shutdown_resources()
