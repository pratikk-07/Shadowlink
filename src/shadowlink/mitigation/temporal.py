"""Temporal coarsening of datetime attributes."""

from __future__ import annotations

from typing import Literal

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.mitigation.models import TransformationLogEntry, TransformationResult

CoarsenLevel = Literal["minute", "hour", "day"]
VALID_LEVELS = frozenset({"minute", "hour", "day"})


def coarsen_timestamp(
    df: pd.DataFrame,
    column: str,
    level: CoarsenLevel,
) -> TransformationResult:
    """Coarsen timestamps by flooring to the specified unit (minute, hour, or day).

    Guarantees no accidental date shifting (e.g. 23:59:59 floored to 'day').
    """
    validate_no_forbidden_columns(df)
    if column not in df.columns:
        raise ValidationError(f"Column '{column}' not found in DataFrame.")

    if level not in VALID_LEVELS:
        raise ValidationError(
            f"Invalid level '{level}'. Must be one of {sorted(VALID_LEVELS)}."
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
            ts = pd.to_datetime(val)
        except Exception as exc:
            raise ValidationError(
                f"Cannot parse timestamp '{val}' in column '{column}': {exc}."
            ) from exc

        # Floor component
        if level == "day":
            coarsened = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        elif level == "hour":
            coarsened = ts.replace(minute=0, second=0, microsecond=0)
        else:  # minute
            coarsened = ts.replace(second=0, microsecond=0)

        # Format as string
        formatted = coarsened.strftime("%Y-%m-%d %H:%M:%S")
        new_values.append(formatted)

        if str(val) != formatted:
            cells_changed += 1
            rows_affected += 1

    new_df[column] = new_values

    log = TransformationLogEntry(
        kind="coarsen_timestamp",
        columns=[column],
        parameters={"level": level},
        rows_affected=rows_affected,
        cells_changed=cells_changed,
        records_suppressed=0,
        notes=f"Timestamps floored to '{level}' precision.",
    )

    return TransformationResult(df=new_df, log=log)
