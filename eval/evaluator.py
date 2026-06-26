"""Retrieval evaluator: runs a gold dataset against the RAG retrieval stack."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.vector_store import VectorStorePort
from eval.dataset import GoldItem
from eval.retrieval_metrics import mean_reciprocal_rank, precision_at_k, recall_at_k


class RetrievalReport(BaseModel):
    """Aggregated retrieval-quality metrics over a dataset."""

    num_queries: int
    top_k: int
    precision_at_k: float
    recall_at_k: float
    mrr: float


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
        rr_pairs: list[tuple[list[str], set[str]]] = []

        for item in dataset:
            retrieved = self._retrieve_sources(item.query, top_k)
            precisions.append(precision_at_k(retrieved, item.relevant_sources, top_k))
            recalls.append(recall_at_k(retrieved, item.relevant_sources, top_k))
            rr_pairs.append((retrieved, item.relevant_sources))

        n = len(dataset)
        return RetrievalReport(
            num_queries=n,
            top_k=top_k,
            precision_at_k=sum(precisions) / n if n else 0.0,
            recall_at_k=sum(recalls) / n if n else 0.0,
            mrr=mean_reciprocal_rank(rr_pairs),
        )
