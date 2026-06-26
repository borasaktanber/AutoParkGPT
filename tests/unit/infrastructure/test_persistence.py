"""Tests for SQL persistence (SQLite in-memory) and in-memory repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autoparkgpt.domain.entities.reservation import Reservation, ReservationStatus
from autoparkgpt.domain.value_objects.car_number import CarNumber
from autoparkgpt.domain.value_objects.reservation_period import ReservationPeriod
from autoparkgpt.infrastructure.config import SQLSettings
from autoparkgpt.infrastructure.persistence import (
    Database,
    InMemoryReservationRepository,
    SqlDynamicDataRepository,
    SqlReservationRepository,
    seed_dynamic_data,
)


@pytest.fixture
def database() -> Database:
    db = Database.from_settings(SQLSettings(url="sqlite+pysqlite:///:memory:"))
    db.create_all()
    return db


def _reservation(first: str = "Ada") -> Reservation:
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)
    return Reservation(
        first_name=first,
        last_name="Lovelace",
        car_number=CarNumber.parse("AB123CD"),
        period=ReservationPeriod(start=start, end=start + timedelta(hours=4)),
    )


def test_sql_reservation_roundtrip(database: Database) -> None:
    repo = SqlReservationRepository(database)
    saved = repo.add(_reservation())
    fetched = repo.get(saved.id)
    assert fetched is not None
    assert fetched.first_name == "Ada"
    assert fetched.car_number.value == "AB123CD"
    assert fetched.status is ReservationStatus.PENDING_APPROVAL


def test_sql_reservation_get_missing(database: Database) -> None:
    assert SqlReservationRepository(database).get("nope") is None


def test_sql_reservation_list_orders_recent_first(database: Database) -> None:
    repo = SqlReservationRepository(database)
    repo.add(_reservation("First"))
    repo.add(_reservation("Second"))
    listed = repo.list_all()
    assert len(listed) == 2


def test_seed_is_idempotent_and_readable(database: Database) -> None:
    seed_dynamic_data(database)
    seed_dynamic_data(database)  # second call must not duplicate
    repo = SqlDynamicDataRepository(database)
    assert len(repo.get_working_hours()) == 7
    assert len(repo.get_prices()) == 2
    assert len(repo.get_availability()) == 2
    assert len(repo.get_availability(zone="A")) == 1


def test_in_memory_repository() -> None:
    repo = InMemoryReservationRepository()
    saved = repo.add(_reservation())
    assert repo.get(saved.id) == saved
    assert repo.get("missing") is None
    assert repo.list_all() == [saved]


def test_sql_update_status_and_list_by_status(database: Database) -> None:
    repo = SqlReservationRepository(database)
    saved = repo.add(_reservation())
    assert len(repo.list_by_status(ReservationStatus.PENDING_APPROVAL)) == 1
    repo.update(saved.approve())
    assert repo.get(saved.id).status is ReservationStatus.APPROVED
    assert repo.list_by_status(ReservationStatus.PENDING_APPROVAL) == []
    assert len(repo.list_by_status(ReservationStatus.APPROVED)) == 1


def test_sql_find_by_reference(database: Database) -> None:
    repo = SqlReservationRepository(database)
    saved = repo.add(_reservation())
    assert repo.find_by_reference(saved.id).id == saved.id
    assert repo.find_by_reference(saved.id[:8]).id == saved.id
    assert repo.find_by_reference("nomatch1") is None


def test_in_memory_find_by_reference_and_status() -> None:
    repo = InMemoryReservationRepository()
    saved = repo.add(_reservation())
    assert repo.find_by_reference(saved.id[:8]).id == saved.id
    repo.update(saved.approve())
    assert repo.list_by_status(ReservationStatus.APPROVED)[0].id == saved.id
