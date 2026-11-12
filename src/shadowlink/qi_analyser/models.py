"""Models for Quasi-Identifier Analyser and Equivalence Classes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

MissingPolicy = Literal["own_group", "exclude_records"]


@dataclass(frozen=True)
class SharedAttributeEntry:
    """Attribute occurrence in a specific dataset."""

    dataset_name: str
    original_name: str
    kind: str
    dtype_compatible: bool


# Canonical attribute name -> list of occurrences across datasets
SharedAttributeMap = dict[str, list[SharedAttributeEntry]]


@dataclass(frozen=True)
class PairwiseOverlap:
    """Attribute overlap indicators between two datasets."""

    dataset_a: str
    dataset_b: str
    shared_column_count: int
    fraction_of_a: float
    fraction_of_b: float


@dataclass(frozen=True)
class OverlapReport:
    """Collection of pairwise overlap indicators."""

    pairs: list[PairwiseOverlap]


CandidateStatus = Literal["suggested", "confirmed", "rejected"]


@dataclass(frozen=True)
class QICandidate:
    """Candidate quasi-identifier attribute flagged by profiling heuristics."""

    column_name: str
    dataset_name: str
    uniqueness_ratio: float | None
    reasons: list[str]
    status: CandidateStatus = "suggested"


@dataclass(frozen=True)
class QIHeuristics:
    """Configurable heuristics for candidate quasi-identifier detection."""

    high_uniqueness_threshold: float = 0.5
    include_shared: bool = True


@dataclass(frozen=True)
class EquivalenceClassResult:
    """Equivalence class partitioning result over quasi-identifiers."""

    qi_columns: list[str]
    total_records: int
    records_analysed: int
    excluded_record_count: int
    class_sizes: list[int]
    num_classes: int
    k: int | None
    singleton_class_count: int
    singleton_record_count: int
    singleton_record_proportion: float | None
    record_class_sizes: pd.Series
    missing_policy: MissingPolicy

    def to_dict(self) -> dict[str, Any]:
        """Convert equivalence class summary to dictionary (omits the full Series)."""
        return {
            "qi_columns": list(self.qi_columns),
            "total_records": self.total_records,
            "records_analysed": self.records_analysed,
            "excluded_record_count": self.excluded_record_count,
            "class_sizes": list(self.class_sizes),
            "num_classes": self.num_classes,
            "k": self.k,
            "singleton_class_count": self.singleton_class_count,
            "singleton_record_count": self.singleton_record_count,
            "singleton_record_proportion": self.singleton_record_proportion,
            "missing_policy": self.missing_policy,
        }
