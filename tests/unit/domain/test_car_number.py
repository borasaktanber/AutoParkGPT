"""Tests for the CarNumber value object."""

from __future__ import annotations

import pytest

from autoparkgpt.domain.exceptions import InvalidCarNumberError
from autoparkgpt.domain.value_objects import CarNumber


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ab 123 cd", "AB 123 CD"),
        ("  XYZ-789  ", "XYZ-789"),
        ("plate1", "PLATE1"),
        ("a1b", "A1B"),
    ],
)
def test_parse_normalizes(raw: str, expected: str) -> None:
    assert CarNumber.parse(raw).value == expected


@pytest.mark.parametrize("raw", ["", "   ", "!", "a", "-AB-", "AB$CD"])
def test_parse_rejects_invalid(raw: str) -> None:
    with pytest.raises(InvalidCarNumberError):
        CarNumber.parse(raw)


def test_custom_pattern() -> None:
    # A strict pattern that only allows exactly 3 letters + 3 digits.
    pattern = r"^[A-Z]{3}[0-9]{3}$"
    assert CarNumber.parse("abc123", pattern=pattern).value == "ABC123"
    with pytest.raises(InvalidCarNumberError):
        CarNumber.parse("ab1234", pattern=pattern)


def test_is_frozen() -> None:
    car = CarNumber.parse("AB123CD")
    with pytest.raises(Exception):  # noqa: B017 - pydantic frozen raises ValidationError
        car.value = "OTHER"  # type: ignore[misc]


def test_str() -> None:
    assert str(CarNumber.parse("ab123")) == "AB123"
