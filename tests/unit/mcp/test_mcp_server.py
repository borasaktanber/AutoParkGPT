"""Tests for the MCP server tools and input validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from autoparkgpt.infrastructure.recording import FileReservationRecorder
from autoparkgpt.mcp_server import build_mcp_server
from autoparkgpt.mcp_server.server import _normalize

_VALID = {
    "name": "Ada Lovelace",
    "car_number": "ab123cd",
    "period_start": "2030-06-01T09:00:00+00:00",
    "period_end": "2030-06-01T13:00:00+00:00",
}


def _recorder(tmp_path: Path) -> FileReservationRecorder:
    return FileReservationRecorder(tmp_path / "reservations.txt")


# ----- input validation (sync) -----
def test_normalize_happy_path() -> None:
    out = _normalize(**_VALID)
    assert out["name"] == "Ada Lovelace"
    assert out["car_number"] == "AB123CD"  # normalized/uppercased


@pytest.mark.parametrize(
    "patch",
    [
        {"car_number": "!!"},  # invalid plate
        {"period_start": "not-a-date"},  # bad datetime
        {"period_end": "2030-06-01T08:00:00+00:00"},  # end <= start
        {"name": "Ada | Lovelace"},  # pipe would forge a column
        {"name": "   "},  # empty
    ],
)
def test_normalize_rejects_bad_input(patch: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        _normalize(**{**_VALID, **patch})


# ----- server tools (async) -----
async def test_tools_registered(tmp_path: Path) -> None:
    server = build_mcp_server(_recorder(tmp_path))
    names = {t.name for t in await server.list_tools()}
    assert names == {"save_reservation", "list_reservations", "find_reservation", "health_check"}


async def test_save_then_list_and_find(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    server = build_mcp_server(recorder)
    await server.call_tool("save_reservation", _VALID)
    await server.call_tool(
        "save_reservation",
        {**_VALID, "name": "Grace Hopper", "car_number": "COBOL59"},
    )
    # Verify via the recorder side effect (independent of FastMCP's return shape).
    records = recorder.list_records()
    assert {r.name for r in records} == {"Ada Lovelace", "Grace Hopper"}
    assert [r.name for r in recorder.find_records("cobol")] == ["Grace Hopper"]


async def test_health_check_reports_count(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    server = build_mcp_server(recorder)
    await server.call_tool("save_reservation", _VALID)
    assert len(recorder.list_records()) == 1
    # health_check should run without error
    await server.call_tool("health_check", {})
