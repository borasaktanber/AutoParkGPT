"""Tests for the Weaviate adapter using a fake client (no server)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument, Visibility
from autoparkgpt.infrastructure.vectorstore import WeaviateVectorStore


class _FakeBatch:
    def __init__(self, sink: list[dict[str, Any]]) -> None:
        self._sink = sink

    def __enter__(self) -> _FakeBatch:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def add_object(self, *, properties: dict[str, Any], uuid: str, vector: list[float]) -> None:
        self._sink.append({"properties": properties, "uuid": uuid, "vector": vector})


class _FakeQuery:
    def __init__(self, objects: list[Any]) -> None:
        self._objects = objects
        self.last_call: dict[str, Any] = {}

    def hybrid(self, **kwargs: Any) -> SimpleNamespace:
        self.last_call = kwargs
        return SimpleNamespace(objects=self._objects)


class _FakeCollection:
    def __init__(self, objects: list[Any]) -> None:
        self.inserted: list[dict[str, Any]] = []
        self.batch = SimpleNamespace(dynamic=lambda: _FakeBatch(self.inserted))
        self.query = _FakeQuery(objects)


class _FakeCollections:
    def __init__(self, objects: list[Any], exists: bool = False) -> None:
        self._collection = _FakeCollection(objects)
        self._exists = exists
        self.created: list[str] = []

    def exists(self, name: str) -> bool:
        return self._exists

    def create(self, *, name: str, **kwargs: Any) -> None:
        self.created.append(name)
        self._exists = True

    def get(self, name: str) -> _FakeCollection:
        return self._collection


class _FakeClient:
    def __init__(self, objects: list[Any] | None = None, exists: bool = False) -> None:
        self.collections = _FakeCollections(objects or [], exists=exists)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _obj(content: str, score: float, title: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        properties={"content": content, "title": title, "source": "faq.md"},
        metadata=SimpleNamespace(score=score),
    )


def test_ensure_schema_creates_when_absent() -> None:
    client = _FakeClient(exists=False)
    store = WeaviateVectorStore(client, "ParkingKnowledge")  # type: ignore[arg-type]
    store.ensure_schema()
    assert client.collections.created == ["ParkingKnowledge"]


def test_ensure_schema_idempotent() -> None:
    client = _FakeClient(exists=True)
    store = WeaviateVectorStore(client, "ParkingKnowledge")  # type: ignore[arg-type]
    store.ensure_schema()
    assert client.collections.created == []


def test_upsert_inserts_objects_with_vectors() -> None:
    client = _FakeClient()
    store = WeaviateVectorStore(client, "ParkingKnowledge")  # type: ignore[arg-type]
    docs = [
        KnowledgeDocument(id="a", content="hours", visibility=Visibility.PUBLIC),
        KnowledgeDocument(id="b", content="prices", visibility=Visibility.INTERNAL),
    ]
    count = store.upsert(docs, [[0.1, 0.2], [0.3, 0.4]])
    assert count == 2
    inserted = client.collections.get("x").inserted
    assert inserted[0]["properties"]["visibility"] == "public"
    assert inserted[1]["properties"]["visibility"] == "internal"


def test_search_maps_results_and_applies_public_filter() -> None:
    objects = [_obj("We are open 24/7", 0.91, title="Hours"), _obj("Rates", 0.5)]
    client = _FakeClient(objects=objects)
    store = WeaviateVectorStore(client, "ParkingKnowledge")  # type: ignore[arg-type]

    chunks = store.search(query_text="hours", query_vector=[0.1], top_k=2, alpha=0.5)

    assert [c.content for c in chunks] == ["We are open 24/7", "Rates"]
    assert chunks[0].score == 0.91
    assert chunks[0].citation() == "Hours"
    # A visibility filter was passed (public_only default).
    assert client.collections.get("x").query.last_call["filters"] is not None


def test_search_without_public_filter() -> None:
    client = _FakeClient(objects=[])
    store = WeaviateVectorStore(client, "ParkingKnowledge")  # type: ignore[arg-type]
    store.search(query_text="q", query_vector=[0.1], top_k=3, alpha=0.5, public_only=False)
    assert client.collections.get("x").query.last_call["filters"] is None


def test_close_delegates() -> None:
    client = _FakeClient()
    WeaviateVectorStore(client, "x").close()  # type: ignore[arg-type]
    assert client.closed
