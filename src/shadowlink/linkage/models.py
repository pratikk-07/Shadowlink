"""Data models for record linkage configuration and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from shadowlink.common.exceptions import ValidationError


@dataclass(frozen=True)
class AttributeComparatorSpec:
    """Specification of comparison method for a pair of attributes."""

    attribute: str
    method: Literal["exact", "numeric", "time", "levenshtein", "jaro", "jaro_winkler"]
    weight: float = 1.0
    parameters: dict[str, Any] = field(default_factory=dict)
    agreement_threshold: float = 0.85

    def __post_init__(self) -> None:
        if not self.attribute.strip():
            raise ValidationError("Attribute name must not be empty.")
        if self.weight <= 0.0:
            raise ValidationError(f"Weight must be > 0.0, got {self.weight}.")
        if not (0.0 <= self.agreement_threshold <= 1.0):
            raise ValidationError(
                f"agreement_threshold must be in [0, 1], got "
                f"{self.agreement_threshold}."
            )


@dataclass(frozen=True)
class FellegiSunterParams:
    """Per-attribute m and u probabilities for Fellegi-Sunter theory."""

    m_probabilities: dict[str, float]
    u_probabilities: dict[str, float]

    def __post_init__(self) -> None:
        for attr, m in self.m_probabilities.items():
            if not (0.0 < m < 1.0):
                raise ValidationError(
                    f"m_probability for '{attr}' must be strictly in (0, 1), got {m}."
                )
        for attr, u in self.u_probabilities.items():
            if not (0.0 < u < 1.0):
                raise ValidationError(
                    f"u_probability for '{attr}' must be strictly in (0, 1), got {u}."
                )
