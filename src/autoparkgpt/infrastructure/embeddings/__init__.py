"""Embedding adapters (Anthropic has no embeddings API)."""

from autoparkgpt.infrastructure.embeddings.factory import build_embedding
from autoparkgpt.infrastructure.embeddings.huggingface import HuggingFaceEmbedding
from autoparkgpt.infrastructure.embeddings.voyage import VoyageEmbedding

__all__ = ["HuggingFaceEmbedding", "VoyageEmbedding", "build_embedding"]
