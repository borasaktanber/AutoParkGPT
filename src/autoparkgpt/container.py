"""Dependency-injection composition root.

The single place where concrete infrastructure adapters are bound to the domain ports.
Application use cases depend only on the ports; the container decides which adapter
implements each one, driven entirely by :class:`Settings`.

Providers are lazy singletons — constructing the container does not connect to Weaviate,
the database, or the LLM until ``chat_service`` (or a specific provider) is first resolved.
Tests override providers with in-memory fakes.
"""

from __future__ import annotations

from dependency_injector import containers, providers
from langgraph.checkpoint.memory import MemorySaver

from autoparkgpt.application.factory import build_chat_service
from autoparkgpt.infrastructure.config import Settings, get_settings
from autoparkgpt.infrastructure.embeddings import build_embedding
from autoparkgpt.infrastructure.guardrails import GuardrailPipeline
from autoparkgpt.infrastructure.llm import AnthropicLLMAdapter
from autoparkgpt.infrastructure.logging import configure_logging
from autoparkgpt.infrastructure.persistence import (
    Database,
    SqlDynamicDataRepository,
    SqlReservationRepository,
)
from autoparkgpt.infrastructure.vectorstore import WeaviateVectorStore


def _init_logging(settings: Settings) -> None:
    configure_logging(level=settings.app.log_level, json_output=settings.app.log_json)


class Container(containers.DeclarativeContainer):
    """Application container binding ports to adapters."""

    settings: providers.Provider[Settings] = providers.Singleton(get_settings)

    logging = providers.Resource(_init_logging, settings=settings)

    # --- infrastructure adapters (each implements a domain port) ---
    guardrail = providers.Singleton(GuardrailPipeline, settings=settings.provided.guardrail)
    database = providers.Singleton(Database.from_settings, settings.provided.sql)
    reservation_repo = providers.Singleton(SqlReservationRepository, database)
    dynamic_data = providers.Singleton(SqlDynamicDataRepository, database)
    embedding = providers.Singleton(build_embedding, settings.provided.embedding)
    llm = providers.Singleton(AnthropicLLMAdapter.from_settings, settings.provided.llm)
    vector_store = providers.Singleton(WeaviateVectorStore.connect, settings.provided.vector_store)

    # LangGraph in-memory checkpointer (per-process). For multi-process production,
    # swap for a Postgres-backed checkpointer (documented future enhancement).
    checkpointer = providers.Singleton(MemorySaver)

    # --- application use case ---
    chat_service = providers.Singleton(
        build_chat_service,
        llm=llm,
        embedding=embedding,
        vector_store=vector_store,
        dynamic_data=dynamic_data,
        guardrail=guardrail,
        reservation_repo=reservation_repo,
        retrieval=settings.provided.retrieval,
        app=settings.provided.app,
        checkpointer=checkpointer,
    )


def build_container() -> Container:
    """Construct and initialize the container."""

    container = Container()
    container.init_resources()
    return container
