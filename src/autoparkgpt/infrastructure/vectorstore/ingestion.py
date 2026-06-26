"""Document ingestion pipeline: load -> chunk -> embed -> index."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter

from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.vector_store import VectorStorePort
from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument
from autoparkgpt.infrastructure.config import RetrievalSettings


def chunk_document(
    document: KnowledgeDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[KnowledgeDocument]:
    """Split a document into overlapping chunks, preserving metadata.

    Short documents (no split needed) are returned unchanged as a single chunk.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    pieces = splitter.split_text(document.content)
    if len(pieces) <= 1:
        return [document]
    return [
        document.model_copy(update={"id": f"{document.id}#chunk{i}", "content": piece})
        for i, piece in enumerate(pieces)
    ]


class IngestionPipeline:
    """Chunks, embeds, and indexes knowledge documents into the vector store."""

    def __init__(
        self,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        settings: RetrievalSettings,
    ) -> None:
        self._embedding = embedding
        self._vector_store = vector_store
        self._settings = settings

    def ingest(self, documents: Sequence[KnowledgeDocument]) -> int:
        """Ingest documents and return the number of chunks indexed."""

        self._vector_store.ensure_schema()

        chunks: list[KnowledgeDocument] = []
        for document in documents:
            chunks.extend(
                chunk_document(
                    document,
                    chunk_size=self._settings.chunk_size,
                    chunk_overlap=self._settings.chunk_overlap,
                )
            )
        if not chunks:
            return 0

        vectors = self._embedding.embed_documents([c.content for c in chunks])
        return self._vector_store.upsert(chunks, vectors)
