"""Car / licence-plate number value object."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from autoparkgpt.domain.exceptions import InvalidCarNumberError

# Default plate pattern (locale-agnostic, documented assumption): 3-16 chars,
# uppercase alphanumerics with optional internal spaces/hyphens, no leading/trailing
# separators. Tighten per a real client's locale via the application config.
DEFAULT_CAR_NUMBER_PATTERN = r"^[A-Z0-9][A-Z0-9 -]{1,14}[A-Z0-9]$"


class CarNumber(BaseModel):
    """A normalized, validated vehicle plate number.

    Normalization: trim, collapse internal whitespace, uppercase. Validation is against
    a configurable regex (default :data:`DEFAULT_CAR_NUMBER_PATTERN`).
    """

    model_config = ConfigDict(frozen=True)

    value: str

    @classmethod
    def parse(cls, raw: str, *, pattern: str = DEFAULT_CAR_NUMBER_PATTERN) -> CarNumber:
        """Normalize and validate a raw plate string.

        Raises:
            InvalidCarNumberError: if the value is empty or does not match ``pattern``.
        """

        normalized = re.sub(r"\s+", " ", raw.strip()).upper()
        if not normalized:
            raise InvalidCarNumberError("Car number must not be empty.")
        if not re.fullmatch(pattern, normalized):
            raise InvalidCarNumberError(
                f"'{raw}' is not a valid car number.",
            )
        return cls(value=normalized)

    def __str__(self) -> str:
        return self.value
