"""Models for the Data Profiler module."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

ColumnKind = Literal["numeric", "categorical", "datetime", "boolean"]


@dataclass(frozen=True)
class ColumnProfile:
    """Statistical profile of a single column in a tabular dataset."""

    name: str
    dtype: str
    kind: ColumnKind
    missing_count: int
    missing_rate: float | None
    distinct_count: int
    uniqueness_ratio: float | None
    is_constant: bool
    is_all_null: bool
    has_mixed_types: bool
    numeric_summary: dict[str, float] | None = None
    categorical_frequencies: list[tuple[Any, int]] | None = None
    datetime_range: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert column profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColumnProfile:
        """Create a ColumnProfile from a dictionary."""
        # Convert categorical frequencies tuples if stored as lists in JSON
        cat_freq = data.get("categorical_frequencies")
        if cat_freq is not None:
            data["categorical_frequencies"] = [tuple(item) for item in cat_freq]
        return cls(**data)


@dataclass(frozen=True)
class DatasetProfile:
    """Summary profile of an entire tabular dataset."""

    dataset_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    duplicate_row_count: int
    memory_bytes: int

    def to_dict(self) -> dict[str, Any]:
        """Convert dataset profile to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [col.to_dict() for col in self.columns],
            "duplicate_row_count": self.duplicate_row_count,
            "memory_bytes": self.memory_bytes,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize dataset profile to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetProfile:
        """Construct DatasetProfile from dictionary representation."""
        cols = [ColumnProfile.from_dict(c) for c in data["columns"]]
        return cls(
            dataset_name=data["dataset_name"],
            row_count=data["row_count"],
            column_count=data["column_count"],
            columns=cols,
            duplicate_row_count=data["duplicate_row_count"],
            memory_bytes=data["memory_bytes"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> DatasetProfile:
        """Deserialize JSON string into DatasetProfile instance."""
        data = json.loads(json_str)
        return cls.from_dict(data)
