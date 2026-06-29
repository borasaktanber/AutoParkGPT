"""Select the reservation recorder backend from configuration."""

from __future__ import annotations

from typing import assert_never

from autoparkgpt.domain.ports.reservation_recorder import ReservationRecorderPort
from autoparkgpt.infrastructure.config import RecordingSettings
from autoparkgpt.infrastructure.recording.file_recorder import FileReservationRecorder
from autoparkgpt.infrastructure.recording.mcp_recorder import McpReservationRecorder


def build_recorder(settings: RecordingSettings) -> ReservationRecorderPort:
    """Return the file recorder (default) or the MCP-client recorder per configuration."""

    match settings.backend:
        case "file":
            return FileReservationRecorder(settings.file_path)
        case "mcp":
            return McpReservationRecorder.from_settings(settings)
        case _:  # pragma: no cover - exhaustiveness guard
            assert_never(settings.backend)
