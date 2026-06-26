"""Tests for the Anthropic LLM adapter (no network)."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from autoparkgpt.domain.value_objects.chat import ChatMessage
from autoparkgpt.infrastructure.config import LLMSettings
from autoparkgpt.infrastructure.llm import AnthropicLLMAdapter, supports_adaptive_thinking


class _StubChatModel:
    """Minimal stand-in for a LangChain BaseChatModel."""

    def __init__(self, response: BaseMessage) -> None:
        self._response = response
        self.received: list[BaseMessage] = []

    def invoke(self, messages: list[BaseMessage]) -> BaseMessage:
        self.received = messages
        return self._response


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("claude-haiku-4-5", False),
        ("claude-sonnet-4-5", False),
        ("claude-sonnet-4-6", True),
        ("claude-opus-4-8", True),
        ("claude-fable-5", True),
    ],
)
def test_supports_adaptive_thinking(model: str, expected: bool) -> None:
    assert supports_adaptive_thinking(model) is expected


def test_generate_returns_text_and_passes_system() -> None:
    stub = _StubChatModel(AIMessage(content="We are open 24/7."))
    adapter = AnthropicLLMAdapter(stub)  # type: ignore[arg-type]

    out = adapter.generate([ChatMessage.user("hours?")], system="be helpful")

    assert out == "We are open 24/7."
    # System prompt is prepended as the first message.
    assert stub.received[0].content == "be helpful"
    assert stub.received[1].content == "hours?"


def test_generate_extracts_text_from_block_list() -> None:
    blocks = [
        {"type": "thinking", "thinking": "hmm"},
        {"type": "text", "text": "Answer is 42."},
    ]
    adapter = AnthropicLLMAdapter(_StubChatModel(AIMessage(content=blocks)))  # type: ignore[arg-type]
    assert adapter.generate([ChatMessage.user("q")]) == "Answer is 42."


def test_from_settings_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API_KEY"):
        AnthropicLLMAdapter.from_settings(LLMSettings(api_key=None))
