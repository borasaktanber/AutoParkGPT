"""Dynamic (SQL-backed) data value objects: working hours, prices, availability."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkingHours(BaseModel):
    """Opening hours for a single day of the week."""

    model_config = ConfigDict(frozen=True)

    day_of_week: int = Field(ge=0, le=6, description="0=Monday ... 6=Sunday")
    opens: str = Field(description="Local opening time, HH:MM, or '' if closed")
    closes: str = Field(description="Local closing time, HH:MM, or '' if closed")
    is_closed: bool = False


class PriceItem(BaseModel):
    """A single tariff line item."""

    model_config = ConfigDict(frozen=True)

    label: str
    amount: float = Field(ge=0.0)
    currency: str = "USD"
    unit: str = Field(description="Billing unit, e.g. 'hour', 'day'")


class Availability(BaseModel):
    """Live availability for a parking zone."""

    model_config = ConfigDict(frozen=True)

    zone: str
    total_spaces: int = Field(ge=0)
    free_spaces: int = Field(ge=0)

    @property
    def is_full(self) -> bool:
        return self.free_spaces == 0
