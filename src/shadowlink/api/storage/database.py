"""SQLAlchemy engine, session factory, and declarative base.

The engine URL is taken from ``api.config.settings.database_url``.
Tests override it via the ``SHADOWLINK_DATABASE_URL`` environment variable
(set to ``sqlite:///:memory:``) before importing this module.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shadowlink.api.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# check_same_thread=False is required for SQLite only; harmless for PG.
_connect_args: dict[str, object] = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def create_tables() -> None:
    """Create all tables (idempotent – used in lifespan and tests)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

