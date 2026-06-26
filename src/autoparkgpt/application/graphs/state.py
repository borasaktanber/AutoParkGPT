"""Typed conversation state for the LangGraph workflow."""

from __future__ import annotations

from typing import TypedDict

from autoparkgpt.application.extraction import Intent
from autoparkgpt.domain.entities.reservation import ReservationDraft, ReservationSlot
from autoparkgpt.domain.value_objects.chat import ChatMessage
from autoparkgpt.domain.value_objects.knowledge import RetrievedChunk

# Human-friendly prompts for each reservation slot.
SLOT_PROMPTS: dict[ReservationSlot, str] = {
    ReservationSlot.FIRST_NAME: "What is your first name?",
    ReservationSlot.LAST_NAME: "And your last name?",
    ReservationSlot.CAR_NUMBER: "What is your car / licence plate number?",
    ReservationSlot.PERIOD: (
        "What is the reservation period? Please give a start and end "
        "date & time (e.g. 2030-06-01 09:00 to 2030-06-01 13:00)."
    ),
}

# Safe, user-facing refusal messages keyed by guardrail category.
REFUSAL_MESSAGES: dict[str, str] = {
    "prompt_injection": (
        "I can only help with parking information and reservations. "
        "How can I help you with your parking today?"
    ),
    "invalid_input": "Sorry, I couldn't read that message. Could you rephrase it?",
    "sensitive_information": (
        "I'm not able to share that. I can help with parking info, hours, "
        "prices, availability, or a reservation."
    ),
}

DEFAULT_REFUSAL = "I'm sorry, I can't help with that. Can I help with your parking instead?"


def refusal_message(category: str) -> str:
    """Return a safe response for a blocked turn."""

    return REFUSAL_MESSAGES.get(category, DEFAULT_REFUSAL)


class ConversationState(TypedDict, total=False):
    """State threaded through the conversation graph and persisted per session."""

    user_input: str
    history: list[ChatMessage]
    intent: Intent
    retrieved: list[RetrievedChunk]
    dynamic_context: str
    draft: ReservationDraft
    # The reservation slot the assistant most recently asked for (drives both
    # slot-aware extraction and "stay in the reservation flow" routing).
    awaiting_slot: ReservationSlot | None
    response: str
    sources: list[str]
    reservation_id: str | None
    blocked: bool


def get_draft(state: ConversationState) -> ReservationDraft:
    """Return the in-progress draft, or a fresh empty one."""

    return state.get("draft") or ReservationDraft()


def get_history(state: ConversationState) -> list[ChatMessage]:
    """Return the conversation history so far."""

    return list(state.get("history") or [])
