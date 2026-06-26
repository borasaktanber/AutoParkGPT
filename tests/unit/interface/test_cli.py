"""Tests for the CLI (commands that do not require external services)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from autoparkgpt import __version__
from autoparkgpt.interface.cli.main import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_ingest_missing_directory() -> None:
    result = runner.invoke(app, ["ingest", "does/not/exist"])
    assert result.exit_code == 1


def test_ingest_empty_directory(tmp_path: Path) -> None:
    result = runner.invoke(app, ["ingest", str(tmp_path)])
    assert result.exit_code == 1
