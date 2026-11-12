"""Risk endpoints — POST /risk, GET /risk/{id}, GET /risks."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from shadowlink.api.dependencies import get_db, resolve_safe_path
from shadowlink.api.schemas.risk import RiskMetricOut, RiskRequest, RiskResponse
from shadowlink.api.storage import repository
from shadowlink.api.storage.models import RiskRecord
from shadowlink.common.exceptions import ShadowlinkError
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.metrics import calculate_class_risk

router = APIRouter(prefix="/risk", tags=["risk"])


def _record_to_response(record: RiskRecord) -> RiskResponse:
    payload = record.payload
    metrics = [RiskMetricOut(**m) for m in payload.get("metrics", [])]
    return RiskResponse(
        id=record.id,
        created_at=record.created_at,
        qi_columns=record.qi_columns,
        metrics=metrics,
        missing_policy=payload.get("missing_policy", "own_group"),
    )


@router.post("", response_model=RiskResponse, status_code=201)
def create_risk(body: RiskRequest, db: Session = Depends(get_db)) -> RiskResponse:
    """Compute k-anonymity risk for a CSV and persist the result."""
    safe_path = resolve_safe_path(body.csv_path)
    try:
        df = pd.read_csv(str(safe_path))
        ec = build_equivalence_classes(
            df,
            body.qi_columns,
            missing_policy=body.missing_policy,  # type: ignore[arg-type]
        )
        report = calculate_class_risk(ec)
    except ShadowlinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Error processing CSV: {exc}"
        ) from exc

    payload = report.to_dict()
    payload["missing_policy"] = body.missing_policy

    record = repository.create_risk(
        db,
        qi_columns=body.qi_columns,
        payload=payload,
    )
    return _record_to_response(record)


@router.get("/{risk_id}", response_model=RiskResponse)
def read_risk(risk_id: int, db: Session = Depends(get_db)) -> RiskResponse:
    record = repository.get_risk(db, risk_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Risk report {risk_id} not found.")
    return _record_to_response(record)


@router.get("", response_model=list[RiskResponse])
def list_risks(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[RiskResponse]:
    records = repository.list_risks(db, limit=limit, offset=offset)
    return [_record_to_response(r) for r in records]

