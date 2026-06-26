"""Claude LLM adapter built on ``langchain-anthropic``.

Implements :class:`LLMPort`. The adapter is capability-aware: adaptive thinking is only
sent to models that support it (Claude 4.6+), so the default economy tier
(``claude-haiku-4-5``) never receives an unsupported parameter.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from autoparkgpt.domain.value_objects.chat import ChatMessage, Role
from autoparkgpt.infrastructure.config import LLMSettings

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

# Model-family substrings that support adaptive thinking + the effort parameter.
ADAPTIVE_THINKING_MODELS: tuple[str, ...] = (
    "opus-4-6",
    "opus-4-7",
    "opus-4-8",
    "sonnet-4-6",
    "fable-5",
    "mythos-5",
)


def supports_adaptive_thinking(model: str) -> bool:
    """Return whether the given model id supports adaptive thinking."""

    return any(family in model for family in ADAPTIVE_THINKING_MODELS)


def _to_langchain(message: ChatMessage) -> BaseMessage:
    match message.role:
        case Role.USER:
            return HumanMessage(content=message.content)
        case Role.ASSISTANT:
            return AIMessage(content=message.content)
        case Role.SYSTEM:
            return SystemMessage(content=message.content)


class AnthropicLLMAdapter:
    """Adapter wrapping a LangChain chat model that talks to Claude."""

    def __init__(self, chat_model: BaseChatModel) -> None:
        self._chat_model = chat_model

    @classmethod
    def from_settings(cls, settings: LLMSettings) -> AnthropicLLMAdapter:
        """Construct the adapter from configuration.

        Raises:
            ValueError: if no Anthropic API key is configured.
        """

        if settings.api_key is None:
            raise ValueError(
                "AUTOPARK_LLM__API_KEY is required to use the Anthropic LLM adapter.",
            )

        kwargs: dict[str, Any] = {
            "model": settings.model,
            "max_tokens": settings.max_tokens,
            "timeout": settings.request_timeout_seconds,
            "api_key": settings.api_key.get_secret_value(),
        }
        if settings.thinking == "adaptive" and supports_adaptive_thinking(settings.model):
            kwargs["thinking"] = {"type": "adaptive"}

        return cls(ChatAnthropic(**kwargs))

    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        # max_tokens is honored at construction time; accepted here for port parity.
        lc_messages: list[BaseMessage] = []
        if system:
            lc_messages.append(SystemMessage(content=system))
        lc_messages.extend(_to_langchain(m) for m in messages)

        response = self._chat_model.invoke(lc_messages)
        return _extract_text(response)


def _extract_text(message: BaseMessage) -> str:
    """Extract plain text from a LangChain message (content may be str or block list)."""

    content = message.content
    if isinstance(content, str):
        return content
    # Content can be a list of block dicts (e.g. with thinking blocks); keep text only.
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)
