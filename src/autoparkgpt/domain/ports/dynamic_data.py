"""Dynamic data port (SQL-backed working hours, prices, availability)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from autoparkgpt.domain.value_objects.dynamic_data import (
    Availability,
    PriceItem,
    WorkingHours,
)


@runtime_checkable
class DynamicDataPort(Protocol):
    """Abstraction over live operational data stored in SQL."""

    def get_working_hours(self) -> list[WorkingHours]:
        """Return the weekly working-hours schedule."""
        ...

    def get_prices(self) -> list[PriceItem]:
        """Return the current tariff."""
        ...

    def get_availability(self, zone: str | None = None) -> list[Availability]:
        """Return live availability, optionally filtered to a single zone."""
        ...
