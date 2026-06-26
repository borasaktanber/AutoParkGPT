"""Immutable domain value objects."""

from autoparkgpt.domain.value_objects.car_number import DEFAULT_CAR_NUMBER_PATTERN, CarNumber
from autoparkgpt.domain.value_objects.chat import ChatMessage, Role
from autoparkgpt.domain.value_objects.dynamic_data import (
    Availability,
    PriceItem,
    WorkingHours,
)
from autoparkgpt.domain.value_objects.knowledge import (
    KnowledgeDocument,
    RetrievedChunk,
    Visibility,
)
from autoparkgpt.domain.value_objects.reservation_period import ReservationPeriod

__all__ = [
    "DEFAULT_CAR_NUMBER_PATTERN",
    "Availability",
    "CarNumber",
    "ChatMessage",
    "KnowledgeDocument",
    "PriceItem",
    "ReservationPeriod",
    "RetrievedChunk",
    "Role",
    "Visibility",
    "WorkingHours",
]
