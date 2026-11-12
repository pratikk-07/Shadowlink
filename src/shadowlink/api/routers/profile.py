"""Profile endpoints — POST /profile, GET /profile/{id}, GET /profiles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from shadowlink.api.dependencies import get_db, resolve_safe_path
from shadowlink.api.schemas.profile import (
    ColumnProfileOut,
    ProfileRequest,
    ProfileResponse,
)
from shadowlink.api.storage import repository
from shadowlink.api.storage.models import ProfileRecord
from shadowlink.common.exceptions import ShadowlinkError
from shadowlink.profiler.profiler import profile_csv

router = APIRouter(prefix="/profile", tags=["profile"])


def _record_to_response(record: ProfileRecord) -> ProfileResponse:
    payload = record.payload
    columns = [ColumnProfileOut(**c) for c in payload.get("columns", [])]
    return ProfileResponse(
        id=record.id,
        dataset_name=record.dataset_name,
        created_at=record.created_at,
        row_count=payload["row_count"],
        column_count=payload["column_count"],
        duplicate_row_count=payload["duplicate_row_count"],
        memory_bytes=payload["memory_bytes"],
        columns=columns,
    )


@router.post("", response_model=ProfileResponse, status_code=201)
def create_profile(
    body: ProfileRequest, db: Session = Depends(get_db)
) -> ProfileResponse:
    """Profile a CSV file and persist the result."""
    safe_path = resolve_safe_path(body.csv_path)
    try:
        dp = profile_csv(
            str(safe_path),
            dataset_name=body.dataset_name,
            parse_dates=body.parse_dates,
        )
    except ShadowlinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record = repository.create_profile(
        db,
        dataset_name=dp.dataset_name,
        payload=dp.to_dict(),
    )
    return _record_to_response(record)


@router.get("/{profile_id}", response_model=ProfileResponse)
def read_profile(profile_id: int, db: Session = Depends(get_db)) -> ProfileResponse:
    record = repository.get_profile(db, profile_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found.")
    return _record_to_response(record)


@router.get("", response_model=list[ProfileResponse])
def list_profiles(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ProfileResponse]:
    records = repository.list_profiles(db, limit=limit, offset=offset)
    return [_record_to_response(r) for r in records]

