"""FastMCP server for the approved-reservations record.

Exposes four tools — ``save_reservation``, ``list_reservations``, ``find_reservation``,
``health_check`` — backed by :class:`FileReservationRecorder`.

Security posture:
- The file path is server-configured and never taken from a tool caller, so no path
  traversal is possible.
- Inputs are validated/normalized (car number via the domain value object, ISO periods,
  length and separator checks) before anything is written; the field separator ``|`` is
  rejected in free-text fields so a caller cannot forge record columns.
- Writes are append-only; ``list``/``find`` are read-only.
- Run over stdio (the standard MCP transport, launched by a trusted host). If exposed over
  HTTP, place it behind an authenticating proxy / token — see the README.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from autoparkgpt.domain.exceptions import InvalidCarNumberError
from autoparkgpt.domain.value_objects.car_number import CarNumber
from autoparkgpt.infrastructure.config import get_settings
from autoparkgpt.infrastructure.recording import FileReservationRecorder

_MAX_FIELD_LEN = 100


def _normalize(name: str, car_number: str, period_start: str, period_end: str) -> dict[str, str]:
    """Validate and normalize save_reservation inputs, or raise ValueError."""

    clean_name = " ".join(name.split())
    if not clean_name or len(clean_name) > _MAX_FIELD_LEN or "|" in clean_name:
        raise ValueError("name must be non-empty, under 100 chars, and contain no '|'.")
    try:
        car = CarNumber.parse(car_number)
    except InvalidCarNumberError as exc:
        raise ValueError(str(exc)) from exc
    try:
        start = datetime.fromisoformat(period_start)
        end = datetime.fromisoformat(period_end)
    except ValueError as exc:
        raise ValueError("period_start/period_end must be ISO-8601 datetimes.") from exc
    if end <= start:
        raise ValueError("period_end must be after period_start.")
    return {
        "name": clean_name,
        "car_number": car.value,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
    }


def build_mcp_server(recorder: FileReservationRecorder) -> FastMCP:
    """Construct the FastMCP server with tools bound to ``recorder``."""

    server = FastMCP("autoparkgpt-reservations")

    @server.tool()
    def save_reservation(
        name: str,
        car_number: str,
        period_start: str,
        period_end: str,
    ) -> dict[str, str]:
        """Append an approved reservation to the records file.

        Args:
            name: full name, e.g. "Ada Lovelace".
            car_number: licence plate.
            period_start: ISO-8601 start datetime.
            period_end: ISO-8601 end datetime.
        """

        fields = _normalize(name, car_number, period_start, period_end)
        record = recorder.append(**fields)
        return record.model_dump()

    @server.tool()
    def list_reservations() -> list[dict[str, str]]:
        """Return all recorded (approved) reservations."""

        return [record.model_dump() for record in recorder.list_records()]

    @server.tool()
    def find_reservation(query: str) -> list[dict[str, str]]:
        """Find recorded reservations by name or car-number substring (case-insensitive)."""

        return [record.model_dump() for record in recorder.find_records(query)]

    @server.tool()
    def health_check() -> dict[str, Any]:
        """Report server health and the number of recorded reservations."""

        return {
            "status": "ok",
            "file": str(recorder.path),
            "count": len(recorder.list_records()),
        }

    return server


def main() -> None:  # pragma: no cover - process entry point
    """Run the MCP server over stdio using the configured records file."""

    settings = get_settings()
    recorder = FileReservationRecorder(settings.recording.file_path)
    build_mcp_server(recorder).run()


if __name__ == "__main__":  # pragma: no cover
    main()
