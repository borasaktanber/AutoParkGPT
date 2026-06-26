"""SQLAlchemy ORM models for dynamic data and reservations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class ReservationModel(Base):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str] = mapped_column(String(128))
    car_number: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkingHoursModel(Base):
    __tablename__ = "working_hours"

    day_of_week: Mapped[int] = mapped_column(Integer, primary_key=True)
    opens: Mapped[str] = mapped_column(String(5), default="")
    closes: Mapped[str] = mapped_column(String(5), default="")
    is_closed: Mapped[bool] = mapped_column(default=False)


class PriceModel(Base):
    __tablename__ = "prices"

    label: Mapped[str] = mapped_column(String(64), primary_key=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    unit: Mapped[str] = mapped_column(String(16))


class AvailabilityModel(Base):
    __tablename__ = "availability"

    zone: Mapped[str] = mapped_column(String(64), primary_key=True)
    total_spaces: Mapped[int] = mapped_column(Integer)
    free_spaces: Mapped[int] = mapped_column(Integer)
