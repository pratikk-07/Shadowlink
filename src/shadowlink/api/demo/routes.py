"""FastAPI route handlers for the SHADOWLINK Demo Dashboard and API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from shadowlink.api.demo.html import DEMO_HTML
from shadowlink.api.demo.models import (
    AttackSimulationRequest,
    CreateRunRequest,
    LinkageRequest,
    MitigationRequest,
    QIAnalysisRequest,
    RunSummaryResponse,
)
from shadowlink.api.demo.service import demo_service

router = APIRouter(tags=["demo"])


def _verify_run(run_id: str) -> None:
    """Ensure run exists in memory or raise a clean 404 error."""
    if not demo_service.has_run(run_id):
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found or has been evicted from memory.",
        )


@router.get("/demo", response_class=HTMLResponse)
def get_demo_dashboard() -> HTMLResponse:
    """Serve the self-contained offline Demo Dashboard HTML."""
    return HTMLResponse(content=DEMO_HTML)


@router.post("/demo/api/runs", response_model=RunSummaryResponse)
def create_run(req: CreateRunRequest) -> RunSummaryResponse:
    """Generate a new synthetic benchmark bundle and profile every dataset."""
    return demo_service.create_run(req)


@router.get("/demo/api/runs/{run_id}/profile")
def get_profile(run_id: str) -> dict[str, Any]:
    """Retrieve detailed profiles for all datasets in the specified run."""
    _verify_run(run_id)
    return demo_service.get_profile(run_id)


@router.post("/demo/api/runs/{run_id}/qi")
def analyze_qi(run_id: str, req: QIAnalysisRequest) -> dict[str, Any]:
    """Analyze quasi-identifiers, equivalence classes, and class-based risk."""
    _verify_run(run_id)
    return demo_service.analyze_qi(run_id, req)


@router.post("/demo/api/runs/{run_id}/attack")
def simulate_attack(
    run_id: str, req: AttackSimulationRequest
) -> dict[str, Any]:
    """Simulate a progressive disclosure re-identification attack."""
    _verify_run(run_id)
    return demo_service.simulate_attack(run_id, req)


@router.post("/demo/api/runs/{run_id}/linkage")
def link_datasets(run_id: str, req: LinkageRequest) -> dict[str, Any]:
    """Execute and evaluate cross-dataset record linkage against ground truth."""
    _verify_run(run_id)
    return demo_service.link_datasets(run_id, req)


@router.post("/demo/api/runs/{run_id}/mitigate")
def mitigate(run_id: str, req: MitigationRequest) -> dict[str, Any]:
    """Apply privacy-preserving mitigations and assess privacy-utility tradeoffs."""
    _verify_run(run_id)
    return demo_service.mitigate(run_id, req)


@router.post("/demo/api/runs/{run_id}/pipeline")
def run_pipeline(run_id: str) -> dict[str, Any]:
    """Execute the full 9-stage pipeline and return comprehensive report data."""
    _verify_run(run_id)
    return demo_service.run_pipeline(run_id)


@router.get("/demo/api/runs/{run_id}/tables")
def get_tables(run_id: str) -> dict[str, Any]:
    """Retrieve benchmark Tables 5, 6, and 7 for the specified run."""
    _verify_run(run_id)
    return demo_service.get_tables(run_id)

