"""Reusable in-memory test doubles for the domain ports.

These let the application layer be tested with zero network / model dependencies.
"""

from __future__ import annotations

from collections.abc import Sequence

from autoparkgpt.domain.entities.reservation import Reservation
from autoparkgpt.domain.ports.guardrail import GuardrailVerdict
from autoparkgpt.domain.value_objects.chat import ChatMessage
from autoparkgpt.domain.value_objects.dynamic_data import (
    Availability,
    PriceItem,
    WorkingHours,
)
from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument, RetrievedChunk


class FakeLLM:
    """LLMPort double that returns scripted replies in order (or echoes)."""

    def __init__(self, replies: Sequence[str] | None = None) -> None:
        self._replies = list(replies or [])
        self.calls: list[list[ChatMessage]] = []
        self.last_system: str | None = None

    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.calls.append(list(messages))
        self.last_system = system
        if self._replies:
            return self._replies.pop(0)
        return messages[-1].content if messages else ""


class FakeEmbedding:
    """EmbeddingPort double producing deterministic small vectors."""

    def __init__(self, dimensions: int = 3) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _vec(self, text: str) -> list[float]:
        # Deterministic, content-dependent but trivial.
        base = float(len(text) % 7)
        return [base + i for i in range(self._dimensions)]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class FakeVectorStore:
    """VectorStorePort double returning preset chunks."""

    def __init__(self, chunks: Sequence[RetrievedChunk] | None = None) -> None:
        self._chunks = list(chunks or [])
        self.ensured = False
        self.upserted: list[KnowledgeDocument] = []

    def ensure_schema(self) -> None:
        self.ensured = True

    def upsert(
        self,
        documents: Sequence[KnowledgeDocument],
        vectors: Sequence[list[float]],
    ) -> int:
        self.upserted.extend(documents)
        return len(documents)

    def search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        top_k: int,
        alpha: float,
        public_only: bool = True,
    ) -> list[RetrievedChunk]:
        return self._chunks[:top_k]


class FakeDynamicData:
    """DynamicDataPort double with fixed operational data."""

    def get_working_hours(self) -> list[WorkingHours]:
        return [WorkingHours(day_of_week=d, opens="00:00", closes="23:59") for d in range(7)]

    def get_prices(self) -> list[PriceItem]:
        return [PriceItem(label="Standard", amount=2.5, unit="hour")]

    def get_availability(self, zone: str | None = None) -> list[Availability]:
        return [Availability(zone="A", total_spaces=100, free_spaces=42)]


class AllowAllGuardrail:
    """GuardrailPort double that allows everything (for graph tests)."""

    def check_input(self, text: str) -> GuardrailVerdict:
        return GuardrailVerdict.ok()

    def scan_output(self, text: str) -> GuardrailVerdict:
        return GuardrailVerdict.ok()


class RecordingAdminNotifier:
    """AdminNotifierPort double that records the reservations it was asked to notify."""

    def __init__(self) -> None:
        self.notified: list[Reservation] = []

    def notify_new_reservation(self, reservation: Reservation) -> None:
        self.notified.append(reservation)


class RecordingUserNotifier:
    """UserNotifierPort double that records decision notifications."""

    def __init__(self) -> None:
        self.decisions: list[Reservation] = []

    def notify_decision(self, reservation: Reservation) -> None:
        self.decisions.append(reservation)


class RecordingReservationRecorder:
    """ReservationRecorderPort double that records what it was asked to persist."""

    def __init__(self) -> None:
        self.recorded: list[Reservation] = []

    def record(self, reservation: Reservation) -> None:
        self.recorded.append(reservation)
