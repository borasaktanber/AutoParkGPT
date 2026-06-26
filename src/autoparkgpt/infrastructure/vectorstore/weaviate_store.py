"""Weaviate vector store adapter implementing :class:`VectorStorePort`.

Supports hybrid (dense + BM25) search with a metadata filter that, by default, restricts
retrieval to ``visibility == public`` documents — internal content is never surfaced to
end users. The Weaviate client is injected so the mapping logic is unit-testable without
a running server; :meth:`connect` builds a real client from settings for the app.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument, RetrievedChunk
from autoparkgpt.infrastructure.config import VectorStoreSettings

if TYPE_CHECKING:
    from weaviate import WeaviateClient


class WeaviateVectorStore:
    """Adapter over a Weaviate v4 client."""

    def __init__(self, client: WeaviateClient, collection_name: str) -> None:
        self._client = client
        self._collection_name = collection_name

    @classmethod
    def connect(cls, settings: VectorStoreSettings) -> WeaviateVectorStore:
        """Open a connection to a local Weaviate instance from settings."""

        import weaviate  # noqa: PLC0415 - optional heavy dependency, imported on use

        client = weaviate.connect_to_local(
            host=settings.host,
            port=settings.http_port,
            grpc_port=settings.grpc_port,
        )
        return cls(client, settings.collection)

    def close(self) -> None:
        """Close the underlying client connection."""

        self._client.close()

    def ensure_schema(self) -> None:
        from weaviate.classes.config import Configure, DataType, Property  # noqa: PLC0415

        if self._client.collections.exists(self._collection_name):
            return
        self._client.collections.create(
            name=self._collection_name,
            # We supply our own vectors (local/Voyage embeddings).
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
                Property(name="visibility", data_type=DataType.TEXT),
            ],
        )

    def upsert(
        self,
        documents: Sequence[KnowledgeDocument],
        vectors: Sequence[list[float]],
    ) -> int:
        if len(documents) != len(vectors):
            raise ValueError("documents and vectors must have the same length.")
        collection = self._client.collections.get(self._collection_name)
        count = 0
        with collection.batch.dynamic() as batch:
            for doc, vector in zip(documents, vectors, strict=True):
                batch.add_object(
                    properties={
                        "content": doc.content,
                        "title": doc.title,
                        "source": doc.source,
                        "visibility": doc.visibility.value,
                    },
                    uuid=_deterministic_uuid(doc.id),
                    vector=vector,
                )
                count += 1
        return count

    def search(
        self,
        *,
        query_text: str,
        query_vector: list[float],
        top_k: int,
        alpha: float,
        public_only: bool = True,
    ) -> list[RetrievedChunk]:
        from weaviate.classes.query import Filter, MetadataQuery  # noqa: PLC0415

        collection = self._client.collections.get(self._collection_name)
        filters = Filter.by_property("visibility").equal("public") if public_only else None
        response = collection.query.hybrid(
            query=query_text,
            vector=query_vector,
            alpha=alpha,
            limit=top_k,
            filters=filters,
            return_metadata=MetadataQuery(score=True),
        )
        return [_to_chunk(obj) for obj in response.objects]


def _deterministic_uuid(source_id: str) -> str:
    """Map a stable document id to a deterministic UUID5 (idempotent upserts)."""

    import uuid  # noqa: PLC0415

    return str(uuid.uuid5(uuid.NAMESPACE_URL, source_id))


def _to_chunk(obj: Any) -> RetrievedChunk:
    props = obj.properties or {}
    score = getattr(obj.metadata, "score", None)
    return RetrievedChunk(
        content=str(props.get("content", "")),
        score=float(score) if score is not None else 0.0,
        title=str(props.get("title", "")),
        source=str(props.get("source", "")),
    )
