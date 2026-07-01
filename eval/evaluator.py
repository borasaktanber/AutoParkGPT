"""Retrieval evaluator: runs a gold dataset against the RAG retrieval stack."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.vector_store import VectorStorePort
from eval.dataset import GoldItem
from eval.retrieval_metrics import (
    average_precision_at_k,
    f1_at_k,
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


class RetrievalReport(BaseModel):
    """Aggregated retrieval-quality metrics over a dataset."""

    num_queries: int
    top_k: int
    precision_at_k: float
    recall_at_k: float
    f1_at_k: float
    hit_rate_at_k: float
    mrr: float
    map: float  # mean average precision
    ndcg_at_k: float


class RetrievalEvaluator:
    """Evaluates retrieval quality through the :class:`VectorStorePort` abstraction."""

    def __init__(
        self,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        *,
        hybrid_alpha: float = 0.5,
    ) -> None:
        self._embedding = embedding
        self._vector_store = vector_store
        self._alpha = hybrid_alpha

    def _retrieve_sources(self, query: str, top_k: int) -> list[str]:
        vector = self._embedding.embed_query(query)
        chunks = self._vector_store.search(
            query_text=query,
            query_vector=vector,
            top_k=top_k,
            alpha=self._alpha,
            public_only=True,
        )
        return [chunk.source for chunk in chunks]

    def evaluate(self, dataset: Sequence[GoldItem], *, top_k: int = 4) -> RetrievalReport:
        precisions: list[float] = []
        recalls: list[float] = []
        f1s: list[float] = []
        hits: list[float] = []
        aps: list[float] = []
        ndcgs: list[float] = []
        rr_pairs: list[tuple[list[str], set[str]]] = []

        for item in dataset:
            retrieved = self._retrieve_sources(item.query, top_k)
            relevant = item.relevant_sources
            precisions.append(precision_at_k(retrieved, relevant, top_k))
            recalls.append(recall_at_k(retrieved, relevant, top_k))
            f1s.append(f1_at_k(retrieved, relevant, top_k))
            hits.append(hit_rate_at_k(retrieved, relevant, top_k))
            aps.append(average_precision_at_k(retrieved, relevant, top_k))
            ndcgs.append(ndcg_at_k(retrieved, relevant, top_k))
            rr_pairs.append((retrieved, relevant))

        n = len(dataset)

        def _mean(values: list[float]) -> float:
            return sum(values) / n if n else 0.0

        return RetrievalReport(
            num_queries=n,
            top_k=top_k,
            precision_at_k=_mean(precisions),
            recall_at_k=_mean(recalls),
            f1_at_k=_mean(f1s),
            hit_rate_at_k=_mean(hits),
            mrr=mean_reciprocal_rank(rr_pairs),
            map=_mean(aps),
            ndcg_at_k=_mean(ndcgs),
        )
