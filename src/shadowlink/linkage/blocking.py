"""Candidate pair generation and multi-pass blocking for record linkage."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns


@dataclass(frozen=True)
class BlockingPass:
    """Specification of one blocking pass with optional attribute transforms."""

    columns: list[str]
    transforms: dict[str, Callable[[Any], Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.columns:
            raise ValidationError("Blocking pass must specify at least one column.")


@dataclass(frozen=True)
class BlockingReport:
    """Summary metrics of candidate pair reduction from blocking."""

    candidate_pairs_count: int
    naive_comparisons: int
    reduction_ratio: float
    passes_applied: int


def _extract_blocking_key(
    row: pd.Series,
    pass_spec: BlockingPass,
) -> tuple[Any, ...] | None:
    """Extract blocking key from row. Returns None if any attribute is missing."""
    key_parts: list[Any] = []
    for col in pass_spec.columns:
        val = row.get(col)
        if val is None or pd.isna(val):
            return None  # Records with missing values are excluded in this pass

        transform_fn = pass_spec.transforms.get(col)
        if transform_fn is not None:
            try:
                transformed_val = transform_fn(val)
            except Exception:
                return None
            key_parts.append(transformed_val)
        else:
            if isinstance(val, str):
                key_parts.append(val.strip().lower())
            else:
                key_parts.append(val)

    return tuple(key_parts)


def generate_candidate_pairs(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    passes: list[BlockingPass],
    left_id_col: str = "record_id",
    right_id_col: str = "record_id",
) -> tuple[pd.DataFrame, BlockingReport]:
    """Generate candidate record pairs across multiple blocking passes.

    Pairs are unioned across passes, deduplicated, and deterministically ordered.
    Records with a missing value in any pass column are not paired in that pass.
    """
    validate_no_forbidden_columns(left_df)
    validate_no_forbidden_columns(right_df)

    if left_id_col not in left_df.columns:
        raise ValidationError(f"ID column '{left_id_col}' missing from left DataFrame.")
    if right_id_col not in right_df.columns:
        raise ValidationError(
            f"ID column '{right_id_col}' missing from right DataFrame."
        )
    if not passes:
        raise ValidationError("At least one BlockingPass must be provided.")

    n_left = len(left_df)
    n_right = len(right_df)
    naive_comparisons = n_left * n_right

    candidate_pairs_set: set[tuple[str, str]] = set()

    for p_spec in passes:
        # Index right dataset
        right_blocks: dict[tuple[Any, ...], list[str]] = defaultdict(list)
        for _, r_row in right_df.iterrows():
            r_key = _extract_blocking_key(r_row, p_spec)
            if r_key is not None:
                right_blocks[r_key].append(str(r_row[right_id_col]))

        # Probe with left dataset
        for _, l_row in left_df.iterrows():
            l_key = _extract_blocking_key(l_row, p_spec)
            if l_key is not None and l_key in right_blocks:
                l_id = str(l_row[left_id_col])
                for r_id in right_blocks[l_key]:
                    candidate_pairs_set.add((l_id, r_id))

    sorted_pairs = sorted(candidate_pairs_set, key=lambda p: (p[0], p[1]))
    pairs_count = len(sorted_pairs)
    reduction = (
        1.0 - (pairs_count / naive_comparisons) if naive_comparisons > 0 else 0.0
    )

    pairs_df = pd.DataFrame(
        {
            "left_id": [p[0] for p in sorted_pairs],
            "right_id": [p[1] for p in sorted_pairs],
        }
    )

    report = BlockingReport(
        candidate_pairs_count=pairs_count,
        naive_comparisons=naive_comparisons,
        reduction_ratio=float(reduction),
        passes_applied=len(passes),
    )

    return pairs_df, report
