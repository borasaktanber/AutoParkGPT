"""LLM-assisted intent classification and reservation-slot extraction.

Both helpers are defensive: the LLM output is parsed robustly and falls back to safe
defaults so a malformed model response never crashes the conversation.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum

from autoparkgpt.application.prompts import INTENT_PROMPT, SLOT_EXTRACTION_PROMPT
from autoparkgpt.domain.ports.llm import LLMPort
from autoparkgpt.domain.value_objects.chat import ChatMessage

_ALLOWED_SLOT_KEYS = {
    "first_name",
    "last_name",
    "car_number",
    "period_start",
    "period_end",
}


class Intent(StrEnum):
    """Routing intents for a user turn."""

    INFO = "INFO"
    DYNAMIC = "DYNAMIC"
    RESERVE = "RESERVE"
    OTHER = "OTHER"


def classify_intent(llm: LLMPort, message: str) -> Intent:
    """Classify a user message into an :class:`Intent` (defaults to INFO on ambiguity)."""

    raw = llm.generate([ChatMessage.user(INTENT_PROMPT.format(message=message))]).strip().upper()
    for intent in Intent:
        if intent.value in raw:
            return intent
    return Intent.INFO


def extract_slots(llm: LLMPort, message: str, *, awaiting: str | None = None) -> dict[str, str]:
    """Extract any provided reservation fields from a message as a string dict.

    ``awaiting`` names the field the assistant just asked for; supplying it helps the
    model map a terse direct answer (e.g. "Bora") to the right slot.
    """

    prompt = SLOT_EXTRACTION_PROMPT.format(message=message)
    if awaiting:
        prompt = (
            f"The assistant just asked the user for their {awaiting}. If the message is a "
            f"direct answer to that question, set the {awaiting} field accordingly.\n\n"
        ) + prompt
    raw = llm.generate([ChatMessage.user(prompt)])
    payload = _parse_json_object(raw)
    return {
        key: str(value)
        for key, value in payload.items()
        if key in _ALLOWED_SLOT_KEYS and isinstance(value, str | int | float) and str(value).strip()
    }


def _parse_json_object(raw: str) -> dict[str, object]:
    """Best-effort extraction of the first JSON object from an LLM response."""

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
