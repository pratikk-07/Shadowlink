"""Pydantic request/response schemas for the profile endpoints.

Safety rule: no request field may be named after a forbidden identity column.
The validator ``_reject_forbidden_fields`` enforces this at schema definition
time (class level) and also at runtime via the model_validator.
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

# Forbidden field names (mirror shadowlink.common.validation.FORBIDDEN_COLUMN_NAMES)
_FORBIDDEN: frozenset[str] = frozenset(
    {"ground_truth", "true_id", "true_identity", "identity_key"}
)


def _check_forbidden_keys(data: dict[str, Any]) -> None:
    """Raise ValueError if any key in *data* matches a forbidden name."""
    for key in data:
        if key.lower().replace(" ", "_") in _FORBIDDEN or key.lower() in _FORBIDDEN:
            raise ValueError(
                f"Field '{key}' is forbidden: SHADOWLINK never accepts identity keys. "
                "Remove this field from your request."
            )


class ProfileRequest(BaseModel):
    """Request body for POST /profile."""

    csv_path: str
    dataset_name: str | None = None
    parse_dates: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            _check_forbidden_keys(values)
        return values

    @field_validator("csv_path")
    @classmethod
    def path_must_be_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("csv_path must not be empty.")
        return v


class ColumnProfileOut(BaseModel):
    """Output representation of a single column's profile."""

    name: str
    dtype: str
    kind: str
    missing_count: int
    missing_rate: float | None
    distinct_count: int
    uniqueness_ratio: float | None
    is_constant: bool
    is_all_null: bool
    has_mixed_types: bool
    numeric_summary: dict[str, Any] | None = None
    top_frequencies: dict[str, int] | None = None
    datetime_range: dict[str, str] | None = None

    model_config = {"from_attributes": True}


class ProfileResponse(BaseModel):
    """Response body for POST /profile and GET /profile/{id}."""

    id: int
    dataset_name: str
    created_at: datetime.datetime
    row_count: int
    column_count: int
    duplicate_row_count: int
    memory_bytes: int
    columns: list[ColumnProfileOut]

    model_config = {"from_attributes": True}

