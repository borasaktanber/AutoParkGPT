"""Guardrail port and verdict value object."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class GuardrailVerdict(BaseModel):
    """Outcome of a guardrail check."""

    model_config = ConfigDict(frozen=True)

    allowed: bool
    category: str = ""
    reason: str = ""

    @classmethod
    def ok(cls) -> GuardrailVerdict:
        return cls(allowed=True)

    @classmethod
    def blocked(cls, category: str, reason: str) -> GuardrailVerdict:
        return cls(allowed=False, category=category, reason=reason)


@runtime_checkable
class GuardrailPort(Protocol):
    """Abstraction over the input/output safety pipeline.

    Implementations protect against prompt injection, jailbreaks, invalid input, and
    leakage of sensitive/internal information in responses.
    """

    def check_input(self, text: str) -> GuardrailVerdict:
        """Validate and screen an incoming user message."""
        ...

    def scan_output(self, text: str) -> GuardrailVerdict:
        """Screen an outgoing assistant message for leakage before it reaches the user."""
        ...
