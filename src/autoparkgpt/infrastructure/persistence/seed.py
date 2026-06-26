"""Seed default dynamic data (idempotent)."""

from __future__ import annotations

from sqlalchemy import select

from autoparkgpt.infrastructure.persistence.database import Database
from autoparkgpt.infrastructure.persistence.models import (
    AvailabilityModel,
    PriceModel,
    WorkingHoursModel,
)


def seed_dynamic_data(database: Database) -> None:
    """Populate working hours, prices, and availability if the tables are empty."""

    with database.session() as session:
        if session.scalar(select(WorkingHoursModel).limit(1)) is None:
            session.add_all(
                WorkingHoursModel(day_of_week=d, opens="06:00", closes="23:00") for d in range(7)
            )
        if session.scalar(select(PriceModel).limit(1)) is None:
            session.add_all(
                [
                    PriceModel(label="Standard", amount=2.5, currency="USD", unit="hour"),
                    PriceModel(label="Daily maximum", amount=20.0, currency="USD", unit="day"),
                ]
            )
        if session.scalar(select(AvailabilityModel).limit(1)) is None:
            session.add_all(
                [
                    AvailabilityModel(zone="A", total_spaces=120, free_spaces=37),
                    AvailabilityModel(zone="B", total_spaces=80, free_spaces=0),
                ]
            )
