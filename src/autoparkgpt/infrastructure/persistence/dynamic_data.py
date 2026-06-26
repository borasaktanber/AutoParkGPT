"""Dynamic data repository implementations (working hours, prices, availability)."""

from __future__ import annotations

from sqlalchemy import select

from autoparkgpt.domain.value_objects.dynamic_data import (
    Availability,
    PriceItem,
    WorkingHours,
)
from autoparkgpt.infrastructure.persistence.database import Database
from autoparkgpt.infrastructure.persistence.models import (
    AvailabilityModel,
    PriceModel,
    WorkingHoursModel,
)


class SqlDynamicDataRepository:
    """SQLAlchemy-backed dynamic data (:class:`DynamicDataPort`)."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def get_working_hours(self) -> list[WorkingHours]:
        with self._db.session() as session:
            stmt = select(WorkingHoursModel).order_by(WorkingHoursModel.day_of_week)
            return [
                WorkingHours(
                    day_of_week=m.day_of_week,
                    opens=m.opens,
                    closes=m.closes,
                    is_closed=m.is_closed,
                )
                for m in session.scalars(stmt)
            ]

    def get_prices(self) -> list[PriceItem]:
        with self._db.session() as session:
            return [
                PriceItem(label=m.label, amount=m.amount, currency=m.currency, unit=m.unit)
                for m in session.scalars(select(PriceModel).order_by(PriceModel.label))
            ]

    def get_availability(self, zone: str | None = None) -> list[Availability]:
        with self._db.session() as session:
            stmt = select(AvailabilityModel)
            if zone is not None:
                stmt = stmt.where(AvailabilityModel.zone == zone)
            return [
                Availability(
                    zone=m.zone,
                    total_spaces=m.total_spaces,
                    free_spaces=m.free_spaces,
                )
                for m in session.scalars(stmt.order_by(AvailabilityModel.zone))
            ]


class StaticDynamicDataRepository:
    """Config-free in-memory dynamic data for tests and demos."""

    def get_working_hours(self) -> list[WorkingHours]:
        return [WorkingHours(day_of_week=d, opens="06:00", closes="23:00") for d in range(7)]

    def get_prices(self) -> list[PriceItem]:
        return [
            PriceItem(label="Standard", amount=2.5, unit="hour"),
            PriceItem(label="Daily maximum", amount=20.0, unit="day"),
        ]

    def get_availability(self, zone: str | None = None) -> list[Availability]:
        zones = [
            Availability(zone="A", total_spaces=120, free_spaces=37),
            Availability(zone="B", total_spaces=80, free_spaces=0),
        ]
        if zone is not None:
            return [a for a in zones if a.zone == zone]
        return zones
