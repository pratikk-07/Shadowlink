"""Health-check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from shadowlink.api.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok", "version": settings.app_version}

