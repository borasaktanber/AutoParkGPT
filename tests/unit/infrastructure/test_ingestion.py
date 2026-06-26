"""Tests for the ingestion pipeline."""

from __future__ import annotations

from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument
from autoparkgpt.infrastructure.config import RetrievalSettings
from autoparkgpt.infrastructure.vectorstore import IngestionPipeline, chunk_document
from tests.fakes import FakeEmbedding, FakeVectorStore


def test_chunk_short_document_is_single_chunk() -> None:
    doc = KnowledgeDocument(id="d1", content="short text")
    chunks = chunk_document(doc, chunk_size=512, chunk_overlap=64)
    assert len(chunks) == 1
    assert chunks[0].id == "d1"


def test_chunk_long_document_splits_with_ids() -> None:
    doc = KnowledgeDocument(id="d1", content="word " * 400)
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    assert chunks[0].id == "d1#chunk0"
    assert all(c.source == doc.source for c in chunks)


def test_pipeline_ingests_and_indexes() -> None:
    embedding = FakeEmbedding(dimensions=3)
    store = FakeVectorStore()
    pipeline = IngestionPipeline(
        embedding,
        store,
        RetrievalSettings(chunk_size=100, chunk_overlap=10),
    )
    docs = [
        KnowledgeDocument(id="a", content="word " * 400),
        KnowledgeDocument(id="b", content="open 24/7"),
    ]
    indexed = pipeline.ingest(docs)
    assert store.ensured
    assert indexed == len(store.upserted)
    assert indexed >= 2  # one multi-chunk doc + one single-chunk doc


def test_pipeline_ingest_empty() -> None:
    pipeline = IngestionPipeline(FakeEmbedding(), FakeVectorStore(), RetrievalSettings())
    assert pipeline.ingest([]) == 0
