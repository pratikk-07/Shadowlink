"""Models for the Mitigation Engine and Privacy-Utility Evaluation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TransformationSpec:
    """Specification of a single privacy transformation to apply in a pipeline."""

    kind: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class TransformationLogEntry:
    """Audit log entry capturing details and effects of an applied transformation."""

    kind: str
    columns: list[str]
    parameters: dict[str, Any]
    rows_affected: int
    cells_changed: int
    records_suppressed: int
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Convert log entry to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class TransformationResult:
    """Output of a pure privacy transformation."""

    df: pd.DataFrame
    log: TransformationLogEntry


@dataclass(frozen=True)
class MitigationReport:
    """Comprehensive comparison of privacy and utility before and after mitigation."""

    before: dict[str, Any]
    after: dict[str, Any]
    suppression_fraction: float
    query_answers: dict[str, tuple[Any, Any]]
    transformation_logs: list[TransformationLogEntry]

    def to_dict(self) -> dict[str, Any]:
        """Convert mitigation report to dictionary."""
        return {
            "before": dict(self.before),
            "after": dict(self.after),
            "suppression_fraction": self.suppression_fraction,
            "query_answers": {k: [v[0], v[1]] for k, v in self.query_answers.items()},
            "transformation_logs": [log.to_dict() for log in self.transformation_logs],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize report to JSON."""
        return json.dumps(self.to_dict(), indent=indent)
