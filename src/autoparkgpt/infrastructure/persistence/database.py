"""Database engine and session factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from autoparkgpt.infrastructure.config import SQLSettings
from autoparkgpt.infrastructure.persistence.models import Base


class Database:
    """Owns the SQLAlchemy engine and produces sessions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @classmethod
    def from_settings(cls, settings: SQLSettings) -> Database:
        engine = create_engine(settings.url, echo=settings.echo, future=True)
        return cls(engine)

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_all(self) -> None:
        """Create all tables (used for local/dev and tests; Alembic handles prod)."""

        Base.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Provide a transactional session scope."""

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
