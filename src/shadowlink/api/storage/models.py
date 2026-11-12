"""ORM models for SHADOWLINK API storage.

Each record stores a JSON payload (the full serialised result object) alongside
lightweight indexed columns for filtering/listing.  No real personal data is
ever written; all payloads come from DatasetProfile.to_dict() and similar pure
library outputs.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shadowlink.api.storage.database import Base


class ProfileRecord(Base):
    """Stored result of a /profile call."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Back-reference so risk records can optionally link to a profile.
    risk_records: Mapped[list["RiskRecord"]] = relationship(
        "RiskRecord", back_populates="profile_record", cascade="all, delete-orphan"
    )


class RiskRecord(Base):
    """Stored result of a /risk call."""

    __tablename__ = "risk_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    qi_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    profile_record: Mapped["ProfileRecord | None"] = relationship(
        "ProfileRecord", back_populates="risk_records"
    )


class MitigationRecord(Base):
    """Stored result of a /mitigate call."""

    __tablename__ = "mitigation_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    specs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    qi_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

