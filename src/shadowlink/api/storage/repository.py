"""CRUD repository functions for SHADOWLINK API storage.

All functions accept a SQLAlchemy ``Session`` and return ORM model instances.
No business logic lives here — only persistence.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from shadowlink.api.storage.models import (
    MitigationRecord,
    ProfileRecord,
    RiskRecord,
)

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def create_profile(
    db: Session,
    dataset_name: str,
    payload: dict[str, Any],
) -> ProfileRecord:
    record = ProfileRecord(dataset_name=dataset_name, payload=payload)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_profile(db: Session, profile_id: int) -> ProfileRecord | None:
    return db.get(ProfileRecord, profile_id)


def list_profiles(
    db: Session, limit: int = 100, offset: int = 0
) -> list[ProfileRecord]:
    return (
        db.query(ProfileRecord)
        .order_by(ProfileRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------


def create_risk(
    db: Session,
    qi_columns: list[str],
    payload: dict[str, Any],
    profile_id: int | None = None,
) -> RiskRecord:
    record = RiskRecord(
        profile_id=profile_id,
        qi_columns=qi_columns,
        payload=payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_risk(db: Session, risk_id: int) -> RiskRecord | None:
    return db.get(RiskRecord, risk_id)


def list_risks(db: Session, limit: int = 100, offset: int = 0) -> list[RiskRecord]:
    return (
        db.query(RiskRecord)
        .order_by(RiskRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Mitigation
# ---------------------------------------------------------------------------


def create_mitigation(
    db: Session,
    specs: list[dict[str, Any]],
    qi_columns: list[str],
    payload: dict[str, Any],
) -> MitigationRecord:
    record = MitigationRecord(
        specs=specs,
        qi_columns=qi_columns,
        payload=payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_mitigation(db: Session, mitigation_id: int) -> MitigationRecord | None:
    return db.get(MitigationRecord, mitigation_id)


def list_mitigations(
    db: Session, limit: int = 100, offset: int = 0
) -> list[MitigationRecord]:
    return (
        db.query(MitigationRecord)
        .order_by(MitigationRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

