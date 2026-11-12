"""Pydantic request/response schemas for the mitigation endpoints."""

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


class TransformationSpecIn(BaseModel):
    """One transformation step specification."""

    kind: str
    parameters: dict[str, Any] = {}

    @field_validator("kind")
    @classmethod
    def kind_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("kind must not be empty.")
        return v


class MitigateRequest(BaseModel):
    """Request body for POST /mitigate."""

    csv_path: str
    qi_columns: list[str]
    specs: list[TransformationSpecIn]

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

    @field_validator("specs")
    @classmethod
    def specs_nonempty(
        cls, v: list[TransformationSpecIn]
    ) -> list[TransformationSpecIn]:
        if not v:
            raise ValueError("specs must contain at least one transformation.")
        return v


class MitigateResponse(BaseModel):
    """Response body for POST /mitigate and GET /mitigate/{id}."""

    id: int
    created_at: datetime.datetime
    qi_columns: list[str]
    specs: list[dict[str, Any]]
    before_k: int | None
    after_k: int | None
    before_avg_risk: float | None
    after_avg_risk: float | None
    records_suppressed: int
    steps_applied: int
    payload: dict[str, Any]

    model_config = {"from_attributes": True}

