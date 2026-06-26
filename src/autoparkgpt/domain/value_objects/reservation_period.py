"""Reservation period value object."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, model_validator

from autoparkgpt.domain.exceptions import InvalidReservationPeriodError


class ReservationPeriod(BaseModel):
    """A half-open booking window ``[start, end)``.

    Enforces ``end > start`` at construction. Window/duration policy that depends on the
    current time and configuration (must be in the future, max duration) is validated
    separately via :meth:`validate_window`, keeping the value object free of clock and
    config coupling.
    """

    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _check_ordering(self) -> ReservationPeriod:
        if self.end <= self.start:
            raise InvalidReservationPeriodError(
                "Reservation end must be strictly after start.",
            )
        return self

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def validate_window(self, *, now: datetime, max_days: int) -> None:
        """Validate the period against the current time and a max-duration policy.

        Raises:
            InvalidReservationPeriodError: if the period starts in the past or exceeds
                the maximum allowed duration.
        """

        if self.start < now:
            raise InvalidReservationPeriodError("Reservation cannot start in the past.")
        if self.duration > timedelta(days=max_days):
            raise InvalidReservationPeriodError(
                f"Reservation duration may not exceed {max_days} days.",
            )
