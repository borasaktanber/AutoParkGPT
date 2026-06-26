"""Reservation repository implementations."""

from __future__ import annotations

from sqlalchemy import select

from autoparkgpt.domain.entities.reservation import Reservation, ReservationStatus
from autoparkgpt.domain.value_objects.car_number import CarNumber
from autoparkgpt.domain.value_objects.reservation_period import ReservationPeriod
from autoparkgpt.infrastructure.persistence.database import Database
from autoparkgpt.infrastructure.persistence.models import ReservationModel


def _to_model(reservation: Reservation) -> ReservationModel:
    return ReservationModel(
        id=reservation.id,
        first_name=reservation.first_name,
        last_name=reservation.last_name,
        car_number=reservation.car_number.value,
        period_start=reservation.period.start,
        period_end=reservation.period.end,
        status=reservation.status.value,
        created_at=reservation.created_at,
    )


def _to_domain(model: ReservationModel) -> Reservation:
    return Reservation(
        id=model.id,
        first_name=model.first_name,
        last_name=model.last_name,
        car_number=CarNumber(value=model.car_number),
        period=ReservationPeriod(start=model.period_start, end=model.period_end),
        status=ReservationStatus(model.status),
        created_at=model.created_at,
    )


class SqlReservationRepository:
    """SQLAlchemy-backed reservation repository (:class:`ReservationRepositoryPort`)."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def add(self, reservation: Reservation) -> Reservation:
        with self._db.session() as session:
            session.add(_to_model(reservation))
        return reservation

    def get(self, reservation_id: str) -> Reservation | None:
        with self._db.session() as session:
            model = session.get(ReservationModel, reservation_id)
            return _to_domain(model) if model is not None else None

    def list_all(self) -> list[Reservation]:
        with self._db.session() as session:
            stmt = select(ReservationModel).order_by(ReservationModel.created_at.desc())
            return [_to_domain(m) for m in session.scalars(stmt)]


class InMemoryReservationRepository:
    """In-memory repository for tests and simple single-process deployments."""

    def __init__(self) -> None:
        self._store: dict[str, Reservation] = {}

    def add(self, reservation: Reservation) -> Reservation:
        self._store[reservation.id] = reservation
        return reservation

    def get(self, reservation_id: str) -> Reservation | None:
        return self._store.get(reservation_id)

    def list_all(self) -> list[Reservation]:
        return sorted(self._store.values(), key=lambda r: r.created_at, reverse=True)
