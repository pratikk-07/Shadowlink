"""FastAPI application factory for SHADOWLINK.

Usage (development):
    uvicorn shadowlink.api.app:app --reload --host 127.0.0.1 --port 8000

The lifespan context manager creates database tables on startup so that
both development runs and test runs with an in-memory SQLite database work
without running Alembic migrations.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shadowlink.api.config import settings
from shadowlink.api.demo import demo_router
from shadowlink.api.routers import health, mitigate, profile, risk
from shadowlink.api.storage.database import create_tables
from shadowlink.common.exceptions import ShadowlinkError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create database tables on startup."""
    create_tables()
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "SHADOWLINK Privacy Re-identification Risk Assessment API. "
        "Defensive use only. No real personal data is accepted or stored."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global exception handler — convert ShadowlinkError to 400 JSON responses
# with no stack traces exposed to the caller.
# ---------------------------------------------------------------------------


@app.exception_handler(ShadowlinkError)
async def shadowlink_error_handler(
    request: Request, exc: ShadowlinkError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Only catch unexpected errors; FastAPI handles HTTP & validation errors.
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal error occurred."},
    )


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(profile.router)
app.include_router(risk.router)
app.include_router(mitigate.router)
app.include_router(demo_router)

