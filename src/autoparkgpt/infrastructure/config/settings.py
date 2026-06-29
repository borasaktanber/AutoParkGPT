"""Typed application configuration.

All configuration is sourced from environment variables (or an `.env` file for local
development). Secrets are **never** hardcoded or committed — they are injected via the
environment only. Nested settings use the delimiter ``__`` and the prefix ``AUTOPARK_``,
e.g. ``AUTOPARK_LLM__MODEL=claude-haiku-4-5``.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingProvider(StrEnum):
    """Supported embedding providers (Anthropic has no embeddings API)."""

    HUGGINGFACE = "huggingface"
    VOYAGE = "voyage"


class LLMSettings(BaseSettings):
    """Claude model configuration.

    The model is a single env var so cost/quality is a deployment choice, not a code
    change. Default is the economy tier (`claude-haiku-4-5`).
    """

    model: str = "claude-haiku-4-5"
    api_key: SecretStr | None = None
    max_tokens: int = Field(default=4096, gt=0)
    # Adaptive thinking is only available on Claude 4.6+ models (Opus 4.6/4.7/4.8,
    # Sonnet 4.6, Fable 5). The adapter ignores this for models that don't support it
    # (e.g. the default Haiku 4.5), so the request never errors.
    thinking: Literal["adaptive", "off"] = "off"
    request_timeout_seconds: float = Field(default=60.0, gt=0)


class EmbeddingSettings(BaseSettings):
    """Embedding provider configuration.

    Defaults to a local HuggingFace model so dev and evaluation are offline,
    deterministic, and free. Voyage is the documented production option.
    """

    provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE
    huggingface_model: str = "BAAI/bge-small-en-v1.5"
    voyage_model: str = "voyage-3"
    voyage_api_key: SecretStr | None = None
    dimensions: int = Field(default=384, gt=0)
    batch_size: int = Field(default=32, gt=0)


class VectorStoreSettings(BaseSettings):
    """Weaviate connection + collection configuration."""

    host: str = "localhost"
    http_port: int = 8080
    grpc_port: int = 50051
    collection: str = "ParkingKnowledge"


class RetrievalSettings(BaseSettings):
    """RAG retrieval + chunking parameters."""

    top_k: int = Field(default=4, gt=0)
    # Hybrid search alpha: 1.0 = pure vector, 0.0 = pure BM25.
    hybrid_alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=64, ge=0)
    min_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class SQLSettings(BaseSettings):
    """SQL database configuration (PostgreSQL in prod, SQLite for tests/local)."""

    url: str = "sqlite+pysqlite:///./autoparkgpt.db"
    echo: bool = False


class GuardrailSettings(BaseSettings):
    """Guardrail thresholds and toggles."""

    max_input_chars: int = Field(default=4000, gt=0)
    enable_injection_detection: bool = True
    enable_output_leakage_scan: bool = True


class AdminSettings(BaseSettings):
    """Stage 2 human-in-the-loop administrator configuration.

    ``api_token`` secures the admin REST endpoints; when unset, those endpoints reject
    every request (fail-closed). Webhook URLs select the notifier adapter — when a URL is
    set the webhook notifier is used, otherwise notifications are logged.
    """

    api_token: SecretStr | None = None
    admin_webhook_url: str | None = None
    user_webhook_url: str | None = None
    notify_timeout_seconds: float = Field(default=10.0, gt=0)


class RecordingSettings(BaseSettings):
    """Stage 3/4 approved-reservation recording.

    ``backend`` selects how approvals are recorded: ``file`` writes the file directly
    (in-process, reliable — the default); ``mcp`` records through the MCP server's
    ``save_reservation`` tool (genuine MCP communication, Stage 4).
    """

    backend: Literal["file", "mcp"] = "file"
    # Path to the approved-reservations text file. Confined to the working directory
    # tree by the recorder; the MCP server never takes a path from clients.
    file_path: str = "data/reservations.txt"


class AppSettings(BaseSettings):
    """General application / server settings."""

    name: str = "AutoParkGPT"
    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    log_json: bool = True
    host: str = "0.0.0.0"  # container binds all interfaces by design
    port: int = Field(default=8000, gt=0)
    # Configurable car-number plate pattern (locale-dependent; documented assumption).
    car_number_pattern: str = r"^[A-Z0-9][A-Z0-9 -]{1,14}[A-Z0-9]$"
    max_reservation_days: int = Field(default=30, gt=0)


class Settings(BaseSettings):
    """Root settings aggregating all configuration groups."""

    model_config = SettingsConfigDict(
        env_prefix="AUTOPARK_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)
    recording: RecordingSettings = Field(default_factory=RecordingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    sql: SQLSettings = Field(default_factory=SQLSettings)
    guardrail: GuardrailSettings = Field(default_factory=GuardrailSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""

    return Settings()
