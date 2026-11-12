"""Mitigation endpoints — POST /mitigate, GET /mitigate/{id}, GET /mitigations."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from shadowlink.api.dependencies import get_db, resolve_safe_path
from shadowlink.api.schemas.mitigate import MitigateRequest, MitigateResponse
from shadowlink.api.storage import repository
from shadowlink.api.storage.models import MitigationRecord
from shadowlink.common.exceptions import ShadowlinkError
from shadowlink.mitigation.models import TransformationSpec
from shadowlink.mitigation.pipeline import run_mitigation_experiment

router = APIRouter(prefix="/mitigate", tags=["mitigate"])


def _record_to_response(record: MitigationRecord) -> MitigateResponse:
    payload = record.payload
    before: dict[str, Any] = payload.get("before", {})
    after: dict[str, Any] = payload.get("after", {})

    def _k(d: dict[str, Any]) -> int | None:
        v = d.get("k")
        return int(v) if v is not None else None

    def _avg(d: dict[str, Any]) -> float | None:
        v = d.get("average_class_risk")
        return float(v) if v is not None else None

    sup_frac = payload.get("suppression_fraction", 0.0)
    orig_count = before.get("record_count", 0)
    records_suppressed = int(round(sup_frac * orig_count)) if orig_count else 0

    return MitigateResponse(
        id=record.id,
        created_at=record.created_at,
        qi_columns=record.qi_columns,
        specs=record.specs,
        before_k=_k(before),
        after_k=_k(after),
        before_avg_risk=_avg(before),
        after_avg_risk=_avg(after),
        records_suppressed=records_suppressed,
        steps_applied=len(record.specs),
        payload=payload,
    )


@router.post("", response_model=MitigateResponse, status_code=201)
def create_mitigation(
    body: MitigateRequest, db: Session = Depends(get_db)
) -> MitigateResponse:
    """Run a mitigation pipeline on a CSV and persist the report."""
    safe_path = resolve_safe_path(body.csv_path)
    try:
        df = pd.read_csv(str(safe_path))
        specs = [
            TransformationSpec(kind=s.kind, parameters=s.parameters)  # type: ignore[arg-type]
            for s in body.specs
        ]
        mit_report = run_mitigation_experiment(df, specs, body.qi_columns)
    except ShadowlinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Error processing CSV: {exc}"
        ) from exc

    specs_dicts = [{"kind": s.kind, "parameters": s.parameters} for s in specs]
    payload = mit_report.to_dict()

    record = repository.create_mitigation(
        db,
        specs=specs_dicts,
        qi_columns=body.qi_columns,
        payload=payload,
    )
    return _record_to_response(record)


@router.get("/{mitigation_id}", response_model=MitigateResponse)
def read_mitigation(
    mitigation_id: int, db: Session = Depends(get_db)
) -> MitigateResponse:
    record = repository.get_mitigation(db, mitigation_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Mitigation {mitigation_id} not found."
        )
    return _record_to_response(record)


@router.get("", response_model=list[MitigateResponse])
def list_mitigations(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MitigateResponse]:
    records = repository.list_mitigations(db, limit=limit, offset=offset)
    return [_record_to_response(r) for r in records]
