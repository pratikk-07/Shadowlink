"""Table aggregation transformations."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns


def aggregate_counts(
    df: pd.DataFrame,
    group_columns: Sequence[str],
) -> pd.DataFrame:
    """Aggregate dataset into a frequency count table grouped by specified columns.

    NOTE: The returned DataFrame is an aggregated frequency table.
    Class-based risk metrics do not apply directly to its rows.
    """
    validate_no_forbidden_columns(df)
    if not group_columns:
        raise ValidationError("group_columns cannot be empty.")

    missing_cols = [c for c in group_columns if c not in df.columns]
    if missing_cols:
        raise ValidationError(f"Columns not found: {missing_cols}.")

    # Group and count
    grouped = df.groupby(list(group_columns), dropna=False, observed=False).size()
    agg_df = grouped.reset_index(name="count")
    return agg_df
