"""Tests for intent classification and slot extraction."""

from __future__ import annotations

from autoparkgpt.application.extraction import Intent, classify_intent, extract_slots
from tests.fakes import FakeLLM


def test_classify_returns_known_intent() -> None:
    assert classify_intent(FakeLLM(["RESERVE"]), "book a spot") is Intent.RESERVE
    assert classify_intent(FakeLLM(["The label is DYNAMIC"]), "prices?") is Intent.DYNAMIC


def test_classify_defaults_to_info_on_garbage() -> None:
    assert classify_intent(FakeLLM(["???"]), "hello") is Intent.INFO


def test_extract_slots_parses_embedded_json() -> None:
    reply = 'Sure: {"first_name": "Ada", "car_number": "AB123CD", "ignored": 1}'
    slots = extract_slots(FakeLLM([reply]), "I am Ada, plate AB123CD")
    assert slots == {"first_name": "Ada", "car_number": "AB123CD"}


def test_extract_slots_handles_invalid_json() -> None:
    assert extract_slots(FakeLLM(["not json at all"]), "hi") == {}


def test_extract_slots_ignores_unknown_and_empty() -> None:
    reply = '{"first_name": "", "last_name": "Doe", "evil": "x"}'
    assert extract_slots(FakeLLM([reply]), "x") == {"last_name": "Doe"}
