"""MCP-client reservation recorder — records via the MCP server's ``save_reservation`` tool.

This is the genuine Stage 4 "MCP communication" path: instead of writing the file
directly, it connects to the MCP server (by default by spawning ``autoparkgpt-mcp`` over
stdio) and calls its tool. The session factory is injectable so the adapter can be tested
against an in-memory server session.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING

import structlog

from autoparkgpt.domain.entities.reservation import Reservation
from autoparkgpt.infrastructure.config import RecordingSettings

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

_logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager["ClientSession"]]


class McpReservationRecorder:
    """Records approved reservations by calling the MCP server's ``save_reservation`` tool."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: RecordingSettings) -> McpReservationRecorder:
        """Build a recorder that spawns the ``autoparkgpt-mcp`` server over stdio."""

        @asynccontextmanager
        async def factory() -> AsyncIterator[ClientSession]:
            from mcp import StdioServerParameters  # noqa: PLC0415 - optional dependency
            from mcp.client.session import ClientSession  # noqa: PLC0415
            from mcp.client.stdio import stdio_client  # noqa: PLC0415

            params = StdioServerParameters(
                command="autoparkgpt-mcp",
                # Merge the environment so the child resolves imports + the same file.
                env={**os.environ, "AUTOPARK_RECORDING__FILE_PATH": settings.file_path},
            )
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                yield session

        return cls(factory)

    def record(self, reservation: Reservation) -> None:
        asyncio.run(self._save(reservation))

    async def _save(self, reservation: Reservation) -> None:
        async with self._session_factory() as session:
            result = await session.call_tool(
                "save_reservation",
                {
                    "name": f"{reservation.first_name} {reservation.last_name}",
                    "car_number": reservation.car_number.value,
                    "period_start": reservation.period.start.isoformat(),
                    "period_end": reservation.period.end.isoformat(),
                },
            )
            if getattr(result, "isError", False):  # pragma: no cover - defensive
                _logger.warning("mcp_save_reservation_error", reservation_id=reservation.id)
