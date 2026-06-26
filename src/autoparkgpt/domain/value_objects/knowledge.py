"""Knowledge-base value objects for RAG."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Visibility(StrEnum):
    """Document visibility — only PUBLIC content is ever retrievable by end users."""

    PUBLIC = "public"
    INTERNAL = "internal"


class KnowledgeDocument(BaseModel):
    """A source document (or chunk) to be embedded and indexed."""

    model_config = ConfigDict(frozen=True)

    id: str
    content: str
    title: str = ""
    source: str = ""
    visibility: Visibility = Visibility.PUBLIC


class RetrievedChunk(BaseModel):
    """A chunk returned from the vector store, with its relevance score and provenance."""

    model_config = ConfigDict(frozen=True)

    content: str
    score: float = Field(ge=0.0)
    title: str = ""
    source: str = ""

    def citation(self) -> str:
        """Human-readable source attribution label."""

        return self.title or self.source or "parking knowledge base"
