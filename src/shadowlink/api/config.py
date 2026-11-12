"""Application settings for SHADOWLINK API.

Uses environment variables with sensible defaults for local development.
No network calls, no real personal data ever processed.
"""

from __future__ import annotations

import os


class Settings:
    """Lightweight settings container.

    Reads from environment variables so no additional dependency is needed.
    For production use, set DATABASE_URL to a PostgreSQL DSN.
    For tests, DATABASE_URL is overridden to sqlite:///:memory:.
    """

    def __init__(self) -> None:
        self.database_url: str = os.environ.get(
            "SHADOWLINK_DATABASE_URL",
            "sqlite:///./shadowlink.db",
        )
        self.data_dir: str = os.environ.get(
            "SHADOWLINK_DATA_DIR",
            "./data",
        )
        self.app_title: str = "SHADOWLINK Privacy Risk API"
        self.app_version: str = "0.1.0"
        self.debug: bool = os.environ.get("SHADOWLINK_DEBUG", "false").lower() == "true"


# Module-level singleton; tests may monkey-patch individual attributes.
settings = Settings()

