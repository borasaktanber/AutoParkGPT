"""Vector store port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument, RetrievedChunk


@runtime_checkable
class VectorStorePort(Protocol):
    """Abstraction over the vector database (Weaviate by default).

    Supports hybrid (dense + keyword) search with metadata filtering. Retrieval is
    restricted to public documents by default so internal content is never surfaced.
    """

    def ensure_schema(self) -> None:
        """Create the collection/schema if it does not already exist (idempotent)."""
        ...

    def upsert(self, documents: Sequence[KnowledgeDocument], vectors: Sequence[list[float]]) -> int:
        """Insert or update documents with their precomputed vectors. Returns the count."""
        ...

    def search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        top_k: int,
        alpha: float,
        public_only: bool = True,
    ) -> list[RetrievedChunk]:
        """Hybrid-search the store and return scored chunks ordered by relevance."""
        ...
