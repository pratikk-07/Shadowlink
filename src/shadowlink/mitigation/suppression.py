"""Suppression transformations: cell-level and row-level suppression."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.mitigation.models import TransformationLogEntry, TransformationResult
from shadowlink.qi_analyser.equivalence import build_equivalence_classes


def suppress_rare_values(
    df: pd.DataFrame,
    column: str,
    minimum_frequency: int,
    replacement: str = "SUPPRESSED",
) -> TransformationResult:
    """Suppress infrequent values whose frequency is < minimum_frequency.

    Unit of suppression is cells. Missing values are left untouched.
    """
    validate_no_forbidden_columns(df)
    if column not in df.columns:
        raise ValidationError(f"Column '{column}' not found in DataFrame.")

    if minimum_frequency <= 1:
        raise ValidationError(
            f"minimum_frequency must be > 1 to suppress rare values, "
            f"got {minimum_frequency}."
        )

    # Check if replacement string already exists as a legitimate value
    existing_vals = set(df[column].dropna().astype(str))
    if replacement in existing_vals:
        raise ValidationError(
            f"Replacement value '{replacement}' already exists in column '{column}'. "
            "Choose a distinct replacement string to avoid semantic collisions."
        )

    counts = df[column].value_counts()
    rare_vals = set(counts[counts < minimum_frequency].index)

    new_df = df.copy(deep=True)
    series = new_df[column]

    new_values: list[object] = []
    cells_changed = 0
    rows_affected = 0

    for val in series:
        if pd.isna(val):
            new_values.append(val)
        elif val in rare_vals:
            new_values.append(replacement)
            cells_changed += 1
            rows_affected += 1
        else:
            new_values.append(val)

    new_df[column] = new_values

    log = TransformationLogEntry(
        kind="suppress_rare_values",
        columns=[column],
        parameters={"minimum_frequency": minimum_frequency, "replacement": replacement},
        rows_affected=rows_affected,
        cells_changed=cells_changed,
        records_suppressed=0,
        notes=(
            f"Suppressed {len(rare_vals)} rare value(s) "
            f"appearing < {minimum_frequency} times."
        ),
    )

    return TransformationResult(df=new_df, log=log)


def suppress_small_classes(
    df: pd.DataFrame,
    qi_columns: Sequence[str],
    k: int,
) -> TransformationResult:
    """Drop records belonging to equivalence classes of size < k.

    Unit of suppression is entire records (rows). Original index is preserved.
    """
    validate_no_forbidden_columns(df)
    if k <= 1:
        raise ValidationError(f"k must be >= 2 for small class suppression, got {k}.")

    eq = build_equivalence_classes(df, qi_columns=qi_columns)
    record_sizes = eq.record_class_sizes

    # Filter out rows where class size < k
    keep_mask = record_sizes >= k
    new_df = df[keep_mask].copy(deep=True)

    records_suppressed = len(df) - len(new_df)

    log = TransformationLogEntry(
        kind="suppress_small_classes",
        columns=list(qi_columns),
        parameters={"k": k},
        rows_affected=records_suppressed,
        cells_changed=0,
        records_suppressed=records_suppressed,
        notes=(
            f"Suppressed {records_suppressed} record(s) "
            f"belonging to classes smaller than {k}."
        ),
    )

    return TransformationResult(df=new_df, log=log)
