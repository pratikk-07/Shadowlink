"""FastAPI dependency and path-safety functions."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from shadowlink.api.config import settings
from shadowlink.api.storage.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def resolve_safe_path(file_path: str | Path) -> Path:
    """Resolve a file path against SHADOWLINK_DATA_DIR and ensure it does not escape.

    Rejects paths outside the allowed data directory (including '../', symlinks outside,
    or absolute paths pointing elsewhere).
    Raises HTTP 400 without leaking any path information.
    """
    try:
        raw = Path(file_path)
        base_dir = Path(settings.data_dir).resolve()
        target = (base_dir / raw).resolve() if not raw.is_absolute() else raw.resolve()
        target.relative_to(base_dir)
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=400,
            detail="Access denied: file path is outside the allowed data directory.",
        )

    if target == base_dir or target.is_dir():
        raise HTTPException(
            status_code=400,
            detail="Access denied: file path is outside the allowed data directory.",
        )

    return target

