"""Domain ports (interfaces).

These ``Protocol`` definitions are the only contract the application layer depends on.
Concrete adapters live in :mod:`autoparkgpt.infrastructure` and are bound to these ports
at the DI composition root.
"""

from autoparkgpt.domain.ports.dynamic_data import DynamicDataPort
from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.guardrail import GuardrailPort, GuardrailVerdict
from autoparkgpt.domain.ports.llm import LLMPort
from autoparkgpt.domain.ports.reservation_repository import ReservationRepositoryPort
from autoparkgpt.domain.ports.vector_store import VectorStorePort

__all__ = [
    "DynamicDataPort",
    "EmbeddingPort",
    "GuardrailPort",
    "GuardrailVerdict",
    "LLMPort",
    "ReservationRepositoryPort",
    "VectorStorePort",
]
