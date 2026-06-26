"""Load static knowledge documents from a directory for ingestion."""

from __future__ import annotations

from pathlib import Path

from autoparkgpt.domain.value_objects.knowledge import KnowledgeDocument, Visibility

_SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_documents(directory: Path) -> list[KnowledgeDocument]:
    """Load all ``.md`` / ``.txt`` files under ``directory`` as public documents.

    The first Markdown heading (``# Title``) or the file stem becomes the title.
    """

    documents: list[KnowledgeDocument] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        documents.append(
            KnowledgeDocument(
                id=str(path.relative_to(directory)),
                content=content,
                title=_extract_title(content, fallback=path.stem),
                source=path.name,
                visibility=Visibility.PUBLIC,
            )
        )
    return documents


def _extract_title(content: str, *, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback
