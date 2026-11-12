"""Models and configurations for the Synthetic Data Generator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from shadowlink.common.exceptions import ConfigError, ValidationError
from shadowlink.common.validation import FORBIDDEN_COLUMN_NAMES


@dataclass(frozen=True)
class DatasetSpec:
    """Specification for a projected dataset."""

    name: str
    attributes: list[str]
    typo_rate: float = 0.0
    missing_rate: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Dataset name must not be empty.")
        if not self.attributes:
            raise ValidationError(
                f"Dataset '{self.name}' must specify at least one attribute."
            )
        for attr in self.attributes:
            if attr.lower() in FORBIDDEN_COLUMN_NAMES:
                raise ValidationError(
                    f"Attribute '{attr}' in dataset '{self.name}' is forbidden."
                )
            if attr == "record_id":
                raise ValidationError(
                    "Attribute 'record_id' is reserved for opaque record ID."
                )
        if not (0.0 <= self.typo_rate <= 1.0):
            raise ValidationError(
                f"typo_rate must be in [0.0, 1.0], got {self.typo_rate}."
            )
        if not (0.0 <= self.missing_rate <= 1.0):
            raise ValidationError(
                f"missing_rate must be in [0.0, 1.0], got {self.missing_rate}."
            )


@dataclass(frozen=True)
class TimestampWindow:
    """Time window for generating synthetic timestamps."""

    start_date: str = "2026-01-01"
    days: int = 30

    def __post_init__(self) -> None:
        if self.days <= 0:
            raise ValidationError(f"days must be > 0, got {self.days}.")


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for synthetic population and dataset generation."""

    seed: int
    population_size: int
    shared_fraction: float
    datasets: list[DatasetSpec]
    timestamp_window: TimestampWindow = field(default_factory=TimestampWindow)
    exclusive_weights: list[float] | None = None

    def __post_init__(self) -> None:
        if self.population_size <= 0:
            raise ValidationError(
                f"population_size must be > 0, got {self.population_size}."
            )
        if not (0.0 <= self.shared_fraction <= 1.0):
            raise ValidationError(
                f"shared_fraction must be in [0.0, 1.0], got {self.shared_fraction}."
            )
        if not self.datasets:
            raise ConfigError("datasets list must contain at least one DatasetSpec.")

        names = [d.name for d in self.datasets]
        if len(names) != len(set(names)):
            raise ConfigError("Dataset names must be unique.")

        if self.exclusive_weights is not None:
            if len(self.exclusive_weights) != len(self.datasets):
                raise ConfigError(
                    f"exclusive_weights length ({len(self.exclusive_weights)}) "
                    f"must match datasets length ({len(self.datasets)})."
                )
            if any(w < 0 for w in self.exclusive_weights):
                raise ConfigError("exclusive_weights must all be non-negative.")
            if sum(self.exclusive_weights) <= 0:
                raise ConfigError("Sum of exclusive_weights must be positive.")

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to JSON-serialisable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class GeneratedBundle:
    """Complete output bundle of synthetic dataset generation."""

    datasets: dict[str, pd.DataFrame]
    ground_truth: pd.DataFrame
    manifest: dict[str, Any]
