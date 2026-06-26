"""Tests for the retrieval evaluator (query-aware fake store)."""

from __future__ import annotations

from autoparkgpt.domain.value_objects.knowledge import RetrievedChunk
from eval.dataset import GoldItem
from eval.evaluator import RetrievalEvaluator
from tests.fakes import FakeEmbedding


class _QueryAwareStore:
    """Returns chunks whose source depends on the query, to exercise the metrics."""

    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self._mapping = mapping

    def ensure_schema(self) -> None:  # pragma: no cover - unused here
        pass

    def upsert(self, documents: object, vectors: object) -> int:  # pragma: no cover
        return 0

    def search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        top_k: int,
        alpha: float,
        public_only: bool = True,
    ) -> list[RetrievedChunk]:
        sources = self._mapping.get(query_text, [])[:top_k]
        return [RetrievedChunk(content="...", score=1.0, source=s) for s in sources]


def test_evaluator_perfect_retrieval() -> None:
    store = _QueryAwareStore(
        {
            "Where is it?": ["location.md", "rules.md"],
            "How to book?": ["reservation_process.md"],
        }
    )
    evaluator = RetrievalEvaluator(FakeEmbedding(), store)  # type: ignore[arg-type]
    dataset = [
        GoldItem(query="Where is it?", relevant_sources={"location.md"}),
        GoldItem(query="How to book?", relevant_sources={"reservation_process.md"}),
    ]
    report = evaluator.evaluate(dataset, top_k=2)

    assert report.num_queries == 2
    assert report.recall_at_k == 1.0  # both relevant docs retrieved within top-2
    assert report.mrr == 1.0  # relevant doc is first for both queries


def test_evaluator_miss() -> None:
    store = _QueryAwareStore({"q": ["wrong.md"]})
    evaluator = RetrievalEvaluator(FakeEmbedding(), store)  # type: ignore[arg-type]
    report = evaluator.evaluate([GoldItem(query="q", relevant_sources={"right.md"})], top_k=2)
    assert report.recall_at_k == 0.0
    assert report.mrr == 0.0
