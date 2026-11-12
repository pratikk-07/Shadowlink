"""Pydantic request and response schemas for the SHADOWLINK Demo Dashboard API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    """Configuration to generate a new synthetic benchmark run."""

    preset: Literal["report_abc", "wide_release"] = "report_abc"
    population_size: int = Field(default=100, ge=50, le=5000)
    shared_fraction: float = Field(default=0.5, ge=0.0, le=1.0)
    typo_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    missing_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    seed: int = Field(default=42, ge=0, le=2147483647)


class RunSummaryResponse(BaseModel):
    """Initial summary returned after creating a synthetic benchmark run."""

    run_id: str
    preset: str
    population_size: int
    shared_fraction: float
    seed: int
    dataset_counts: dict[str, int]
    dataset_previews: dict[str, list[dict[str, Any]]]
    dataset_profiles: dict[str, Any]
    stage_status: dict[str, str]


class QIAnalysisRequest(BaseModel):
    """Request quasi-identifier and equivalence class risk computation."""

    dataset_name: str
    qi_columns: list[str] = Field(min_length=1)


class AttackSimulationRequest(BaseModel):
    """Request progressive disclosure re-identification attack simulation."""

    dataset_name: str = "A"
    steps: list[list[str]] = Field(
        default_factory=lambda: [["age", "city"], ["course"]]
    )
    n_targets: int = Field(default=25, ge=1, le=500)
    seed: int = Field(default=42, ge=0)


class LinkageRequest(BaseModel):
    """Request cross-dataset record linkage evaluation."""

    left_dataset: str = "A"
    right_dataset: str = "B"
    method: Literal[
        "deterministic", "similarity", "fellegi_sunter", "compare_all"
    ] = "similarity"
    attributes: list[str] = Field(default_factory=lambda: ["age", "city"])
    blocking_keys: list[str] = Field(default_factory=lambda: ["city"])
    threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class MitigationRequest(BaseModel):
    """Request privacy mitigation pipeline execution with before/after analysis."""

    dataset_name: str = "A"
    qi_columns: list[str] = Field(default_factory=lambda: ["age", "city"])
    transformations: list[dict[str, Any]] = Field(default_factory=list)

