"""Tests for the MCP-client recorder and the recorder-selection factory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from mcp.shared.memory import create_connected_server_and_client_session

from autoparkgpt.domain.entities.reservation import Reservation, ReservationDraft
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod
from autoparkgpt.infrastructure.config import RecordingSettings
from autoparkgpt.infrastructure.recording import (
    FileReservationRecorder,
    McpReservationRecorder,
    build_recorder,
)
from autoparkgpt.mcp_server import build_mcp_server


def _reservation() -> Reservation:
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationDraft(
        first_name="Ada",
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    ).to_reservation()


def test_build_recorder_selects_backend(tmp_path: Path) -> None:
    file_settings = RecordingSettings(backend="file", file_path=str(tmp_path / "r.txt"))
    assert isinstance(build_recorder(file_settings), FileReservationRecorder)
    assert isinstance(build_recorder(RecordingSettings(backend="mcp")), McpReservationRecorder)


def test_mcp_recorder_saves_through_server(tmp_path: Path) -> None:
    # The MCP recorder talks to the MCP server (here, an in-memory session), which writes
    # via its own file recorder — exercising real client -> server -> file communication.
    backing = FileReservationRecorder(tmp_path / "r.txt")
    server = build_mcp_server(backing)
    recorder = McpReservationRecorder(lambda: create_connected_server_and_client_session(server))

    recorder.record(_reservation())  # sync entry point (asyncio.run internally)

    records = backing.list_records()
    assert len(records) == 1
    assert records[0].name == "Ada Lovelace"
    assert records[0].car_number == "AB123CD"
