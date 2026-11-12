"""Pydantic request/response schemas for the risk endpoints."""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

_FORBIDDEN: frozenset[str] = frozenset(
    {"ground_truth", "true_id", "true_identity", "identity_key"}
)


def _check_forbidden_keys(data: dict[str, Any]) -> None:
    for key in data:
        if key.lower().replace(" ", "_") in _FORBIDDEN or key.lower() in _FORBIDDEN:
            raise ValueError(
                f"Field '{key}' is forbidden: SHADOWLINK never accepts identity keys."
            )


class RiskRequest(BaseModel):
    """Request body for POST /risk."""

    csv_path: str
    qi_columns: list[str]
    missing_policy: str = "own_group"

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            _check_forbidden_keys(values)
        return values

    @field_validator("csv_path")
    @classmethod
    def path_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("csv_path must not be empty.")
        return v

    @field_validator("qi_columns")
    @classmethod
    def columns_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("qi_columns must contain at least one column name.")
        return v


class RiskMetricOut(BaseModel):
    name: str
    value: float | None
    denominator: str
    formula: str
    assumption: str
    source_module: str
    explanation: str

    model_config = {"from_attributes": True}


class RiskResponse(BaseModel):
    """Response body for POST /risk and GET /risk/{id}."""

    id: int
    created_at: datetime.datetime
    qi_columns: list[str]
    metrics: list[RiskMetricOut]
    missing_policy: str

    model_config = {"from_attributes": True}

