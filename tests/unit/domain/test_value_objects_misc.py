"""Tests for chat, knowledge, dynamic-data value objects and guardrail verdict."""

from __future__ import annotations

from autoparkgpt.domain.ports import GuardrailVerdict
from autoparkgpt.domain.value_objects import (
    Availability,
    ChatMessage,
    KnowledgeDocument,
    PriceItem,
    RetrievedChunk,
    Role,
    Visibility,
    WorkingHours,
)


def test_chat_message_factories() -> None:
    assert ChatMessage.user("hi").role is Role.USER
    assert ChatMessage.assistant("yo").role is Role.ASSISTANT
    assert ChatMessage.system("sys").role is Role.SYSTEM


def test_knowledge_document_defaults_public() -> None:
    doc = KnowledgeDocument(id="1", content="hours are 24/7")
    assert doc.visibility is Visibility.PUBLIC


def test_retrieved_chunk_citation_prefers_title() -> None:
    assert RetrievedChunk(content="x", score=0.9, title="Pricing").citation() == "Pricing"
    assert RetrievedChunk(content="x", score=0.5, source="faq.md").citation() == "faq.md"
    assert RetrievedChunk(content="x", score=0.1).citation() == "parking knowledge base"


def test_availability_is_full() -> None:
    assert Availability(zone="A", total_spaces=10, free_spaces=0).is_full
    assert not Availability(zone="A", total_spaces=10, free_spaces=3).is_full


def test_price_and_hours_value_objects() -> None:
    price = PriceItem(label="Standard", amount=2.5, unit="hour")
    assert price.currency == "USD"
    hours = WorkingHours(day_of_week=6, opens="", closes="", is_closed=True)
    assert hours.is_closed


def test_guardrail_verdict_factories() -> None:
    assert GuardrailVerdict.ok().allowed
    blocked = GuardrailVerdict.blocked("prompt_injection", "detected override attempt")
    assert not blocked.allowed
    assert blocked.category == "prompt_injection"
