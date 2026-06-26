"""Tests for embedding adapters (backends mocked — no torch/network)."""

from __future__ import annotations

import pytest

from autoparkgpt.infrastructure.config import EmbeddingProvider, EmbeddingSettings
from autoparkgpt.infrastructure.embeddings import (
    HuggingFaceEmbedding,
    VoyageEmbedding,
    build_embedding,
)


class _FakeEncoder:
    def encode(self, sentences: list[str], **kwargs: object) -> list[list[float]]:
        return [[float(len(s)), 1.0, 2.0] for s in sentences]


class _FakeVoyageResult:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self.embeddings = embeddings


class _FakeVoyageClient:
    def __init__(self) -> None:
        self.last_input_type: str | None = None

    def embed(self, texts: list[str], *, model: str, input_type: str) -> _FakeVoyageResult:
        self.last_input_type = input_type
        return _FakeVoyageResult([[float(len(t)), 0.5, 0.25] for t in texts])


def test_huggingface_embed_documents_and_query() -> None:
    emb = HuggingFaceEmbedding(_FakeEncoder(), dimensions=3)
    assert emb.dimensions == 3
    docs = emb.embed_documents(["ab", "abcd"])
    assert docs == [[2.0, 1.0, 2.0], [4.0, 1.0, 2.0]]
    assert emb.embed_query("xyz") == [3.0, 1.0, 2.0]


def test_huggingface_empty_documents() -> None:
    assert HuggingFaceEmbedding(_FakeEncoder(), dimensions=3).embed_documents([]) == []


def test_voyage_uses_input_type() -> None:
    client = _FakeVoyageClient()
    emb = VoyageEmbedding(client, model="voyage-3", dimensions=3)
    emb.embed_documents(["hello"])
    assert client.last_input_type == "document"
    emb.embed_query("q")
    assert client.last_input_type == "query"


def test_voyage_requires_key() -> None:
    settings = EmbeddingSettings(provider=EmbeddingProvider.VOYAGE, voyage_api_key=None)
    with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
        VoyageEmbedding.from_settings(settings)


def test_factory_selects_huggingface(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = HuggingFaceEmbedding(_FakeEncoder(), dimensions=3)
    monkeypatch.setattr(
        HuggingFaceEmbedding,
        "from_settings",
        classmethod(lambda cls, settings: sentinel),
    )
    built = build_embedding(EmbeddingSettings(provider=EmbeddingProvider.HUGGINGFACE))
    assert built is sentinel
