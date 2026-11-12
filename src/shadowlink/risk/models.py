"""Models for the Risk Engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class RiskMetric:
    """Individual, explainable privacy risk indicator (Non-Negotiable Rule R3)."""

    name: str
    value: float | None
    denominator: str
    formula: str
    assumption: str
    source_module: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskMetric:
        """Construct RiskMetric from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class RiskReport:
    """Comprehensive privacy risk assessment report.

    Contains separate, named indicators only. No composite or aggregate score.
    """

    metrics: list[RiskMetric]
    per_record_risk: pd.Series

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "record_count": len(self.per_record_risk),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskReport:
        """Construct RiskReport from dictionary."""
        metrics = [RiskMetric.from_dict(m) for m in data["metrics"]]
        # Restore empty Series if per_record_risk was not persisted in summary dict
        series = pd.Series([], dtype="float64")
        return cls(metrics=metrics, per_record_risk=series)

    @classmethod
    def from_json(cls, json_str: str) -> RiskReport:
        """Deserialize JSON string into RiskReport."""
        data = json.loads(json_str)
        return cls.from_dict(data)

