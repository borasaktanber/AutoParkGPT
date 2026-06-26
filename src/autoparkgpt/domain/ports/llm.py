"""LLM port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from autoparkgpt.domain.value_objects.chat import ChatMessage


@runtime_checkable
class LLMPort(Protocol):
    """Abstraction over a chat LLM.

    Kept deliberately text-in/text-out so it is trivial to mock and so the application
    layer is independent of any SDK. Intent routing is done via instructed structured
    output parsed by the application, not native tool-calling (introduced in Stage 4).
    """

    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate an assistant reply for the given conversation."""
        ...
