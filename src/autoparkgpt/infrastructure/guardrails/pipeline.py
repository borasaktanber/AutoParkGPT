"""Composable guardrail pipeline implementing :class:`GuardrailPort`."""

from __future__ import annotations

from autoparkgpt.domain.ports.guardrail import GuardrailVerdict
from autoparkgpt.infrastructure.config import GuardrailSettings
from autoparkgpt.infrastructure.guardrails.patterns import (
    INJECTION_PATTERNS,
    LEAKAGE_PATTERNS,
)


class GuardrailPipeline:
    """A small, ordered pipeline of input/output safety checks.

    Input pipeline: structural validation -> prompt-injection / jailbreak detection.
    Output pipeline: leakage scan for system-prompt / internal / secret content.

    Each stage is independently testable and toggled via :class:`GuardrailSettings`.
    """

    def __init__(self, settings: GuardrailSettings) -> None:
        self._settings = settings

    # ----- input ------------------------------------------------------------ #
    def check_input(self, text: str) -> GuardrailVerdict:
        stripped = text.strip()
        if not stripped:
            return GuardrailVerdict.blocked("invalid_input", "Message must not be empty.")
        if len(text) > self._settings.max_input_chars:
            return GuardrailVerdict.blocked(
                "invalid_input",
                f"Message exceeds the {self._settings.max_input_chars}-character limit.",
            )
        if self._settings.enable_injection_detection:
            for pattern in INJECTION_PATTERNS:
                if pattern.search(text):
                    return GuardrailVerdict.blocked(
                        "prompt_injection",
                        "Message matched a prompt-injection / jailbreak heuristic.",
                    )
        return GuardrailVerdict.ok()

    # ----- output ----------------------------------------------------------- #
    def scan_output(self, text: str) -> GuardrailVerdict:
        if self._settings.enable_output_leakage_scan:
            for pattern in LEAKAGE_PATTERNS:
                if pattern.search(text):
                    return GuardrailVerdict.blocked(
                        "sensitive_information",
                        "Response matched a sensitive-information leakage heuristic.",
                    )
        return GuardrailVerdict.ok()
