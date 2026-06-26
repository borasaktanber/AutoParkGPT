"""Factory selecting the configured embedding provider."""

from __future__ import annotations

from typing import assert_never

from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.infrastructure.config import EmbeddingProvider, EmbeddingSettings
from autoparkgpt.infrastructure.embeddings.huggingface import HuggingFaceEmbedding
from autoparkgpt.infrastructure.embeddings.voyage import VoyageEmbedding


def build_embedding(settings: EmbeddingSettings) -> EmbeddingPort:
    """Construct the embedding adapter selected by configuration.

    Importing the adapter classes is cheap — each defers its heavy backend import
    (``sentence_transformers`` / ``voyageai``) to ``from_settings``.
    """

    match settings.provider:
        case EmbeddingProvider.HUGGINGFACE:
            return HuggingFaceEmbedding.from_settings(settings)
        case EmbeddingProvider.VOYAGE:
            return VoyageEmbedding.from_settings(settings)
        case _:  # pragma: no cover - exhaustiveness guard
            assert_never(settings.provider)
