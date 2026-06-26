"""Voyage AI embedding adapter (documented production option).

Voyage is Anthropic's recommended embeddings partner. The ``voyageai`` import is deferred
to construction so the module stays importable without the dependency present.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from autoparkgpt.infrastructure.config import EmbeddingSettings


class _VoyageClient(Protocol):
    """Minimal interface we rely on from the Voyage client."""

    def embed(self, texts: list[str], *, model: str, input_type: str) -> object: ...


class VoyageEmbedding:
    """Embedding adapter backed by the Voyage AI API."""

    def __init__(self, client: _VoyageClient, model: str, dimensions: int) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions

    @classmethod
    def from_settings(cls, settings: EmbeddingSettings) -> VoyageEmbedding:
        # Lazy import: only require the voyageai package when this provider is used.
        import voyageai  # noqa: PLC0415

        if settings.voyage_api_key is None:
            raise ValueError(
                "AUTOPARK_EMBEDDING__VOYAGE_API_KEY is required for the Voyage provider.",
            )
        client = voyageai.Client(  # type: ignore[attr-defined]
            api_key=settings.voyage_api_key.get_secret_value(),
        )
        return cls(client, model=settings.voyage_model, dimensions=settings.dimensions)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _embed(self, texts: Sequence[str], input_type: str) -> list[list[float]]:
        if not texts:
            return []
        result = self._client.embed(list(texts), model=self._model, input_type=input_type)
        embeddings: list[list[float]] = result.embeddings  # type: ignore[attr-defined]
        return [[float(x) for x in row] for row in embeddings]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, input_type="document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], input_type="query")[0]
