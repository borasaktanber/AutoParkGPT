"""Embedding port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingPort(Protocol):
    """Abstraction over a text-embedding model (local HuggingFace or Voyage)."""

    @property
    def dimensions(self) -> int:
        """The embedding vector dimensionality."""
        ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of documents for indexing."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for retrieval."""
        ...
