"""Numeric binning into half-open intervals [a, b)."""

from __future__ import annotations

from typing import Literal, Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.mitigation.models import TransformationLogEntry, TransformationResult


def bin_numeric(
    df: pd.DataFrame,
    column: str,
    edges: Sequence[float],
    labels: Sequence[str] | None = None,
    out_of_range: Literal["suppress", "error"] = "suppress",
    replacement: str = "SUPPRESSED",
) -> TransformationResult:
    """Discretize numeric column into intervals [edges[i], edges[i+1])."""
    validate_no_forbidden_columns(df)
    if column not in df.columns:
        raise ValidationError(f"Column '{column}' not found in DataFrame.")

    if len(edges) < 2:
        raise ValidationError("edges must contain at least 2 boundary values.")

    # Check edges are strictly increasing
    for i in range(len(edges) - 1):
        if edges[i] >= edges[i + 1]:
            raise ValidationError(
                f"edges must be strictly increasing: {edges[i]} >= {edges[i + 1]}."
            )

    num_bins = len(edges) - 1
    if labels is not None and len(labels) != num_bins:
        raise ValidationError(
            f"Number of labels ({len(labels)}) must match number of bins ({num_bins})."
        )

    bin_labels: list[str] = (
        list(labels)
        if labels is not None
        else [f"[{edges[i]},{edges[i + 1]})" for i in range(num_bins)]
    )

    new_df = df.copy(deep=True)
    series = new_df[column]

    new_values: list[object] = []
    cells_changed = 0
    rows_affected = 0

    for val in series:
        if pd.isna(val):
            new_values.append(val)
            continue

        try:
            num = float(val)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                f"Non-numeric value '{val}' in column '{column}': {exc}."
            ) from exc

        # Check range: [edges[0], edges[-1])
        if num < edges[0] or num >= edges[-1]:
            if out_of_range == "error":
                raise ValidationError(
                    f"Value {num} is outside interval [{edges[0]}, {edges[-1]})."
                )
            new_values.append(replacement)
            cells_changed += 1
            rows_affected += 1
            continue

        # Find bin
        assigned_label: str | None = None
        for i in range(num_bins):
            if edges[i] <= num < edges[i + 1]:
                assigned_label = bin_labels[i]
                break

        new_values.append(assigned_label)
        cells_changed += 1
        rows_affected += 1

    new_df[column] = new_values

    log = TransformationLogEntry(
        kind="bin_numeric",
        columns=[column],
        parameters={"edges": list(edges), "labels": bin_labels},
        rows_affected=rows_affected,
        cells_changed=cells_changed,
        records_suppressed=0,
        notes=f"Numeric column partitioned into {num_bins} bins.",
    )

    return TransformationResult(df=new_df, log=log)
