"""Generalization transformations: age binning and hierarchy lookups."""

from __future__ import annotations

import math
from typing import Literal, Mapping

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.mitigation.models import TransformationLogEntry, TransformationResult


def generalize_age(
    df: pd.DataFrame,
    column: str,
    bin_width: int,
    base: int = 0,
    valid_min: int = 0,
    valid_max: int = 120,
    out_of_range: Literal["suppress", "error"] = "suppress",
    replacement: str = "SUPPRESSED",
) -> TransformationResult:
    """Generalize integer-valued ages into discrete interval labels 'lo-hi'.

    Parameters
    ----------
    df:
        Input DataFrame. Never mutated.
    column:
        Age column name.
    bin_width:
        Width of each age bin (e.g. 5 gives 20-24, 25-29). Must be > 0.
    base:
        Starting baseline offset (default 0).
    valid_min:
        Minimum valid age.
    valid_max:
        Maximum valid age.
    out_of_range:
        Action when value < valid_min or > valid_max ('suppress' or 'error').
    replacement:
        String replacement when value is out of range and suppressed.

    Returns
    -------
    TransformationResult
    """
    validate_no_forbidden_columns(df)
    if column not in df.columns:
        raise ValidationError(f"Column '{column}' not found in DataFrame.")

    if bin_width <= 0:
        raise ValidationError(f"bin_width must be > 0, got {bin_width}.")

    new_df = df.copy(deep=True)
    series = new_df[column]

    # Verify integer-valued non-null ages
    non_nulls = series.dropna()
    for val in non_nulls:
        if isinstance(val, (int, float)):
            if not float(val).is_integer():
                raise ValidationError(
                    f"Column '{column}' requires integer-valued ages, got {val}. "
                    "For continuous floating-point attributes, use bin_numeric instead."
                )
        else:
            try:
                f_val = float(val)
                if not f_val.is_integer():
                    raise ValidationError(
                        f"Column '{column}' requires integer-valued ages, got '{val}'."
                    )
            except (ValueError, TypeError) as exc:
                raise ValidationError(
                    f"Column '{column}' contains unparseable age '{val}': {exc}."
                ) from exc

    cells_changed = 0
    rows_affected = 0
    new_values: list[object] = []

    for val in series:
        if pd.isna(val):
            new_values.append(val)
            continue

        int_val = int(val)
        if int_val < valid_min or int_val > valid_max:
            if out_of_range == "error":
                raise ValidationError(
                    f"Age {int_val} out of valid range [{valid_min}, {valid_max}]."
                )
            new_values.append(replacement)
            cells_changed += 1
            rows_affected += 1
            continue

        # Compute bin [lo, hi]
        lo = base + math.floor((int_val - base) / bin_width) * bin_width
        hi = lo + bin_width - 1
        label = f"{lo}-{hi}"

        new_values.append(label)
        cells_changed += 1
        rows_affected += 1

    new_df[column] = new_values

    log = TransformationLogEntry(
        kind="generalize_age",
        columns=[column],
        parameters={
            "bin_width": bin_width,
            "base": base,
            "valid_min": valid_min,
            "valid_max": valid_max,
        },
        rows_affected=rows_affected,
        cells_changed=cells_changed,
        records_suppressed=0,
        notes=f"Ages generalized into {bin_width}-year intervals.",
    )

    return TransformationResult(df=new_df, log=log)


def generalize_by_hierarchy(
    df: pd.DataFrame,
    column: str,
    mapping: Mapping[str, str],
    unmapped: Literal["suppress", "error", "keep"] = "suppress",
    replacement: str = "SUPPRESSED",
) -> TransformationResult:
    """Generalize categorical values using a lookup hierarchy mapping."""
    validate_no_forbidden_columns(df)
    if column not in df.columns:
        raise ValidationError(f"Column '{column}' not found in DataFrame.")

    new_df = df.copy(deep=True)
    series = new_df[column]

    new_values: list[object] = []
    cells_changed = 0
    rows_affected = 0

    for val in series:
        if pd.isna(val):
            new_values.append(val)
            continue

        str_val = str(val)
        if str_val in mapping:
            mapped_val = mapping[str_val]
            new_values.append(mapped_val)
            if mapped_val != str_val:
                cells_changed += 1
                rows_affected += 1
        else:
            if unmapped == "error":
                raise ValidationError(
                    f"Unmapped value '{str_val}' in column '{column}'."
                )
            elif unmapped == "suppress":
                new_values.append(replacement)
                cells_changed += 1
                rows_affected += 1
            else:  # keep
                new_values.append(str_val)

    new_df[column] = new_values

    log = TransformationLogEntry(
        kind="generalize_by_hierarchy",
        columns=[column],
        parameters={"unmapped_policy": unmapped},
        rows_affected=rows_affected,
        cells_changed=cells_changed,
        records_suppressed=0,
        notes=(
            f"Hierarchy mapping generalization applied ({len(mapping)} keys)."
        ),
    )
    return TransformationResult(df=new_df, log=log)
