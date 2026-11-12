"""Shared pytest fixtures for API tests.

Uses an in-memory SQLite database so tests never need a real PostgreSQL server.
The ``SHADOWLINK_DATABASE_URL`` environment variable is patched BEFORE the
database module is imported, so the engine is created with the correct URL.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Patch DB URL and DATA_DIR BEFORE any app import.
# ---------------------------------------------------------------------------
os.environ["SHADOWLINK_DATABASE_URL"] = "sqlite:///:memory:"
_FIXTURES_DIR = str(Path(__file__).resolve().parent.parent / "fixtures")
os.environ.setdefault("SHADOWLINK_DATA_DIR", _FIXTURES_DIR)

from shadowlink.api.app import app  # noqa: E402
from shadowlink.api.config import settings  # noqa: E402
from shadowlink.api.dependencies import get_db  # noqa: E402
from shadowlink.api.storage.database import Base  # noqa: E402

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


def _override_get_db() -> object:
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db() -> object:
    """Create all tables fresh for every test; drop them afterwards."""
    Base.metadata.create_all(bind=_TEST_ENGINE)
    orig_data_dir = settings.data_dir
    settings.data_dir = _FIXTURES_DIR
    yield
    settings.data_dir = orig_data_dir
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient with the DB dependency overridden to in-memory SQLite."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()

