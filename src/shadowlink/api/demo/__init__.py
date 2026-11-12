"""SHADOWLINK Demo Dashboard API package."""

from __future__ import annotations

from shadowlink.api.demo.routes import router as demo_router
from shadowlink.api.demo.service import demo_service

__all__ = ["demo_service", "demo_router"]
