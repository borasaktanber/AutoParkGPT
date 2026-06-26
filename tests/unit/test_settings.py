"""Unit tests for configuration loading."""

from __future__ import annotations

import pytest

from autoparkgpt.infrastructure.config import Settings, get_settings


def test_defaults_are_sensible() -> None:
    settings = Settings()
    assert settings.app.name == "AutoParkGPT"
    # Economy tier is the shipped default.
    assert settings.llm.model == "claude-haiku-4-5"
    assert settings.embedding.provider.value == "huggingface"
    assert settings.retrieval.top_k > 0


def test_env_overrides_nested_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOPARK_LLM__MODEL", "claude-opus-4-8")
    monkeypatch.setenv("AUTOPARK_RETRIEVAL__TOP_K", "9")
    settings = Settings()
    assert settings.llm.model == "claude-opus-4-8"
    assert settings.retrieval.top_k == 9


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_api_key_is_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOPARK_LLM__API_KEY", "sk-secret-value")
    settings = Settings()
    assert settings.llm.api_key is not None
    # Secret value must not leak through the default string representation.
    assert "sk-secret-value" not in str(settings.llm.api_key)
    assert settings.llm.api_key.get_secret_value() == "sk-secret-value"
