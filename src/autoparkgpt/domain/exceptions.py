"""Domain-level exceptions.

These are framework-agnostic and carry no infrastructure detail. Adapters translate
infrastructure failures into these (or their own infra exceptions), and the interface
layer maps them to safe, user-facing responses.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""


class ValidationError(DomainError):
    """Raised when a value object or entity invariant is violated."""


class InvalidCarNumberError(ValidationError):
    """Raised when a car/plate number fails validation."""


class InvalidReservationPeriodError(ValidationError):
    """Raised when a reservation period is invalid (ordering, window, duration)."""


class ReservationError(DomainError):
    """Raised for reservation lifecycle / persistence problems."""


class GuardrailViolationError(DomainError):
    """Raised when input or output is blocked by a guardrail.

    Attributes:
        category: machine-readable violation category (e.g. ``prompt_injection``).
        reason: human-readable explanation (safe to log; never echo raw user payloads).
    """

    def __init__(self, category: str, reason: str) -> None:
        self.category = category
        self.reason = reason
        super().__init__(f"{category}: {reason}")


class RetrievalError(DomainError):
    """Raised when knowledge retrieval fails."""
