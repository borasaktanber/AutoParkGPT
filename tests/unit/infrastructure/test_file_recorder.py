"""Tests for the approved-reservation file recorder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from autoparkgpt.domain.entities.reservation import ReservationDraft
from autoparkgpt.domain.value_objects import CarNumber, ReservationPeriod
from autoparkgpt.infrastructure.recording import FileReservationRecorder, RecordedReservation


def _reservation(first: str = "Ada", last: str = "Lovelace", plate: str = "AB123CD"):
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return ReservationDraft(
        first_name=first,
        last_name=last,
        car_number=CarNumber.parse(plate),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    ).to_reservation()


def _recorder(tmp_path: Path) -> FileReservationRecorder:
    fixed = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
    return FileReservationRecorder(tmp_path / "reservations.txt", clock=lambda: fixed)


def test_record_writes_spec_format(tmp_path: Path) -> None:
    rec = _recorder(tmp_path)
    rec.record(_reservation())
    line = (tmp_path / "reservations.txt").read_text(encoding="utf-8").strip()
    # Name | Car Number | Reservation Period | Approval Time
    assert line == (
        "Ada Lovelace | AB123CD | "
        "2030-06-01T09:00:00+00:00 - 2030-06-01T13:00:00+00:00 | "
        "2026-06-26T12:00:00+00:00"
    )


def test_list_records_parses_back(tmp_path: Path) -> None:
    rec = _recorder(tmp_path)
    rec.record(_reservation("Ada", "Lovelace", "AB123CD"))
    rec.record(_reservation("Grace", "Hopper", "COBOL59"))
    records = rec.list_records()
    assert [r.name for r in records] == ["Ada Lovelace", "Grace Hopper"]
    assert records[0].car_number == "AB123CD"
    assert records[0].approval_time == "2026-06-26T12:00:00+00:00"


def test_find_records_by_name_and_car(tmp_path: Path) -> None:
    rec = _recorder(tmp_path)
    rec.record(_reservation("Ada", "Lovelace", "AB123CD"))
    rec.record(_reservation("Grace", "Hopper", "COBOL59"))
    assert [r.name for r in rec.find_records("hopper")] == ["Grace Hopper"]
    assert [r.car_number for r in rec.find_records("ab123")] == ["AB123CD"]
    assert rec.find_records("nobody") == []
    assert rec.find_records("  ") == []


def test_list_empty_when_no_file(tmp_path: Path) -> None:
    assert _recorder(tmp_path).list_records() == []


def test_parse_rejects_malformed_lines() -> None:
    assert RecordedReservation.parse("just one field") is None
    assert RecordedReservation.parse("a | b | no-sep-period | t") is None
    good = RecordedReservation.parse("Ada | AB1 | 2030-01-01T00:00 - 2030-01-01T01:00 | t")
    assert good is not None
    assert good.car_number == "AB1"
