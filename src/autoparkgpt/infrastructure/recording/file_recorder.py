"""Append-only text-file recorder for approved reservations.

Writes one line per approved reservation in the spec format:

    Name | Car Number | Reservation Period | Approval Time

Reliability: a process-level lock serializes writes, and each append is flushed and
``fsync``-ed. Security: the file path is server-configured (never client-supplied) and
resolved once at construction, so MCP tool callers cannot influence where data is written.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from autoparkgpt.domain.entities.reservation import Reservation

_FIELD_SEP = " | "
_PERIOD_SEP = " - "


class RecordedReservation(BaseModel):
    """A parsed line from the approved-reservations file."""

    model_config = ConfigDict(frozen=True)

    name: str
    car_number: str
    period_start: str
    period_end: str
    approval_time: str

    def to_line(self) -> str:
        period = f"{self.period_start}{_PERIOD_SEP}{self.period_end}"
        return _FIELD_SEP.join([self.name, self.car_number, period, self.approval_time])

    @classmethod
    def parse(cls, line: str) -> RecordedReservation | None:
        parts = [p.strip() for p in line.split(_FIELD_SEP)]
        if len(parts) != 4:  # noqa: PLR2004 - exactly the 4 spec fields
            return None
        name, car_number, period, approval_time = parts
        if _PERIOD_SEP not in period:
            return None
        start, end = (p.strip() for p in period.split(_PERIOD_SEP, 1))
        return cls(
            name=name,
            car_number=car_number,
            period_start=start,
            period_end=end,
            approval_time=approval_time,
        )


class FileReservationRecorder:
    """Records approved reservations to a text file (:class:`ReservationRecorderPort`)."""

    def __init__(
        self,
        file_path: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = Path(file_path).resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record(self, reservation: Reservation) -> None:
        """Append the approved reservation to the file (thread-safe, durable)."""

        self.append(
            name=f"{reservation.first_name} {reservation.last_name}",
            car_number=reservation.car_number.value,
            period_start=reservation.period.start.isoformat(),
            period_end=reservation.period.end.isoformat(),
        )

    def append(
        self,
        *,
        name: str,
        car_number: str,
        period_start: str,
        period_end: str,
        approval_time: str | None = None,
    ) -> RecordedReservation:
        """Append a record from explicit fields (used by the MCP save tool)."""

        record = RecordedReservation(
            name=name.strip(),
            car_number=car_number.strip(),
            period_start=period_start.strip(),
            period_end=period_end.strip(),
            approval_time=approval_time or self._clock().isoformat(),
        )
        with self._lock, self._path.open("a", encoding="utf-8") as fh:
            fh.write(record.to_line() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return record

    def list_records(self) -> list[RecordedReservation]:
        """Return all recorded reservations (oldest first)."""

        if not self._path.exists():
            return []
        with self._lock:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        parsed = [RecordedReservation.parse(line) for line in lines if line.strip()]
        return [record for record in parsed if record is not None]

    def find_records(self, query: str) -> list[RecordedReservation]:
        """Return records whose name or car number contains ``query`` (case-insensitive)."""

        needle = query.strip().lower()
        if not needle:
            return []
        return [
            record
            for record in self.list_records()
            if needle in record.name.lower() or needle in record.car_number.lower()
        ]
