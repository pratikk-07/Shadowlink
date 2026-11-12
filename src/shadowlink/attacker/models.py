"""Data structures and configuration models for the Attacker Simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from shadowlink.common.exceptions import ValidationError


@dataclass(frozen=True)
class KnowledgeSpec:
    """Matching criteria specification for an attribute."""

    kind: Literal["exact", "numeric_tolerance", "time_window"] = "exact"
    tolerance: float = 0.0
    window_minutes: int = 0

    def __post_init__(self) -> None:
        if self.kind == "numeric_tolerance" and self.tolerance < 0:
            raise ValidationError(
                f"Numeric tolerance cannot be negative, got {self.tolerance}."
            )
        if self.kind == "time_window" and self.window_minutes < 0:
            raise ValidationError(
                f"Time window cannot be negative, got {self.window_minutes}."
            )


@dataclass(frozen=True)
class AttackerProfile:
    """Multi-step attacker profile representing progressive attribute acquisition."""

    name: str
    steps: list[tuple[str, ...]]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("AttackerProfile name must not be empty.")
        if not self.steps:
            raise ValidationError("AttackerProfile must have at least one step.")
        for idx, step in enumerate(self.steps):
            if not step:
                raise ValidationError(f"Step {idx} in profile must not be empty.")

    @classmethod
    def weak(cls) -> AttackerProfile:
        """Single step: demographic baseline (age, city)."""
        return cls(name="weak", steps=[("age", "city")])

    @classmethod
    def moderate(cls) -> AttackerProfile:
        """Two steps: demographic baseline + course."""
        return cls(name="moderate", steps=[("age", "city"), ("course",)])

    @classmethod
    def strong(cls) -> AttackerProfile:
        """Four steps: age+city -> course -> location -> timestamp."""
        return cls(
            name="strong",
            steps=[
                ("age", "city"),
                ("course",),
                ("location",),
                ("timestamp",),
            ],
        )


@dataclass(frozen=True)
class StepMetricReport:
    """Summary indicators for one step of progressive re-identification."""

    step: int
    attributes: list[str]
    cumulative_attributes: list[str]
    mean_candidates: float
    median_candidates: float
    min_candidates: int
    max_candidates: int
    mean_risk: float
    mean_reduction: float
    unique_fraction: float
    expected_success_rate: float
    simulated_success_rate: float
    skipped_attributes_count: int


@dataclass(frozen=True)
class AttackResult:
    """Complete results from an attacker simulation experiment."""

    profile_name: str
    target_count: int
    total_records: int
    step_reports: list[StepMetricReport]
    candidate_sizes_per_target: dict[int, list[int]] = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Export step metrics as a tidy DataFrame."""
        rows: list[dict[str, Any]] = []
        for r in self.step_reports:
            rows.append(
                {
                    "step": r.step,
                    "attributes": "+".join(r.attributes),
                    "cumulative_attributes": "+".join(r.cumulative_attributes),
                    "mean_candidates": r.mean_candidates,
                    "median_candidates": r.median_candidates,
                    "min_candidates": r.min_candidates,
                    "max_candidates": r.max_candidates,
                    "mean_risk": r.mean_risk,
                    "mean_reduction": r.mean_reduction,
                    "unique_fraction": r.unique_fraction,
                    "expected_success_rate": r.expected_success_rate,
                    "simulated_success_rate": r.simulated_success_rate,
                }
            )
        return pd.DataFrame(rows)

