"""Local HuggingFace sentence-transformers embedding adapter (default provider).

The heavy ``sentence_transformers`` / ``torch`` import is deferred to construction so the
module can be imported (and the rest of the app type-checked / unit-tested) without the
ML stack installed.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, cast

from autoparkgpt.infrastructure.config import EmbeddingSettings


class _Encoder(Protocol):
    """Minimal interface we rely on from a sentence-transformers model.

    ``encode`` returns a numpy array at runtime; typed as ``Any`` so the adapter can
    iterate rows without depending on numpy's type stubs.
    """

    def encode(self, sentences: Sequence[str], **kwargs: Any) -> Any: ...


class HuggingFaceEmbedding:
    """Embedding adapter backed by a local sentence-transformers model."""

    def __init__(self, model: _Encoder, dimensions: int, batch_size: int = 32) -> None:
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    @classmethod
    def from_settings(cls, settings: EmbeddingSettings) -> HuggingFaceEmbedding:
        # Lazy import: keep the heavy torch stack out of the import path unless the
        # HuggingFace provider is actually selected and constructed.
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        # Cast to our minimal Protocol — the real `encode` signature is far broader than
        # the slice we use, and we only depend on the documented behaviour.
        model = cast(_Encoder, SentenceTransformer(settings.huggingface_model))
        return cls(model, dimensions=settings.dimensions, batch_size=settings.batch_size)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
        )
        return [[float(x) for x in row] for row in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
