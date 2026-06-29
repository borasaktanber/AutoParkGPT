"""Tests for LangSmith tracing configuration."""

from __future__ import annotations

import os

import pytest

from autoparkgpt.infrastructure.config import ObservabilitySettings
from autoparkgpt.infrastructure.observability import configure_tracing

_TRACING_VARS = (
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENDPOINT",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TRACING_VARS:
        monkeypatch.delenv(var, raising=False)


def test_disabled_when_tracing_off(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = ObservabilitySettings(tracing=False, api_key="lsv2_secret")  # type: ignore[arg-type]
    assert configure_tracing(settings) is False
    assert "LANGSMITH_TRACING" not in os.environ


def test_disabled_when_no_api_key() -> None:
    assert configure_tracing(ObservabilitySettings(tracing=True, api_key=None)) is False


def test_enabled_exports_standard_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = ObservabilitySettings(
        tracing=True,
        api_key="lsv2_secret",  # type: ignore[arg-type]
        project="autoparkgpt",
        endpoint="https://eu.api.smith.langchain.com",
    )
    assert configure_tracing(settings) is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "lsv2_secret"
    assert os.environ["LANGSMITH_PROJECT"] == "autoparkgpt"
    assert os.environ["LANGSMITH_ENDPOINT"] == "https://eu.api.smith.langchain.com"


def test_does_not_override_existing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_PROJECT", "deployment-set")
    configure_tracing(ObservabilitySettings(tracing=True, api_key="lsv2_secret"))  # type: ignore[arg-type]
    assert os.environ["LANGSMITH_PROJECT"] == "deployment-set"  # deployment wins
