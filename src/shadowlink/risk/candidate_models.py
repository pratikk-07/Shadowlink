"""Models for Candidate-Set Risk assessment."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CandidateStepRisk:
    """Risk indicators for a single candidate narrowing step."""

    step: int
    candidate_count: int
    risk: float | None
    candidate_reduction: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert step risk to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class CandidateRiskReport:
    """Report evaluating candidate-set shrinkage as knowledge grows."""

    initial_count: int
    steps: list[CandidateStepRisk]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "initial_count": self.initial_count,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize report to JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateRiskReport:
        """Construct CandidateRiskReport from dictionary."""
        steps = [CandidateStepRisk(**s) for s in data["steps"]]
        return cls(initial_count=data["initial_count"], steps=steps)

    @classmethod
    def from_json(cls, json_str: str) -> CandidateRiskReport:
        """Deserialize JSON string into CandidateRiskReport."""
        return cls.from_dict(json.loads(json_str))

