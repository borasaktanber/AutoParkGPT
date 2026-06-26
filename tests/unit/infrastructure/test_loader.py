"""Tests for the static knowledge loader."""

from __future__ import annotations

from pathlib import Path

from autoparkgpt.domain.value_objects.knowledge import Visibility
from autoparkgpt.infrastructure.vectorstore import load_documents


def test_loads_md_and_txt_with_titles(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Hours\nWe are open 24/7.", encoding="utf-8")
    (tmp_path / "b.txt").write_text("Plain note about parking.", encoding="utf-8")
    (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")
    (tmp_path / "empty.md").write_text("   ", encoding="utf-8")

    docs = load_documents(tmp_path)

    assert {d.source for d in docs} == {"a.md", "b.txt"}
    by_source = {d.source: d for d in docs}
    assert by_source["a.md"].title == "Hours"  # from heading
    assert by_source["b.txt"].title == "b"  # fallback to stem
    assert all(d.visibility is Visibility.PUBLIC for d in docs)


def test_empty_directory_returns_nothing(tmp_path: Path) -> None:
    assert load_documents(tmp_path) == []
