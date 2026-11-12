"""Spatial coarsening of geographic coordinate attributes."""

from __future__ import annotations

import numpy as np
import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.mitigation.models import TransformationLogEntry, TransformationResult


def coarsen_coordinates(
    df: pd.DataFrame,
    lat_column: str,
    lon_column: str,
    decimals: int = 2,
) -> TransformationResult:
    """Coarsen latitude and longitude coordinates by rounding to specified decimals."""
    validate_no_forbidden_columns(df)
    for col in (lat_column, lon_column):
        if col not in df.columns:
            raise ValidationError(f"Column '{col}' not found in DataFrame.")

    if decimals < 0:
        raise ValidationError(f"decimals must be >= 0, got {decimals}.")

    new_df = df.copy(deep=True)

    lat_orig = new_df[lat_column]
    lon_orig = new_df[lon_column]

    try:
        lat_rounded = np.round(
            pd.to_numeric(lat_orig, errors="raise"), decimals=decimals
        )
        lon_rounded = np.round(
            pd.to_numeric(lon_orig, errors="raise"), decimals=decimals
        )
    except Exception as exc:
        raise ValidationError(f"Coordinates must be numeric: {exc}.") from exc

    # Count changes
    lat_diff = (lat_orig != lat_rounded) & lat_orig.notna()
    lon_diff = (lon_orig != lon_rounded) & lon_orig.notna()
    cells_changed = int(lat_diff.sum() + lon_diff.sum())
    rows_affected = int((lat_diff | lon_diff).sum())

    new_df[lat_column] = lat_rounded
    new_df[lon_column] = lon_rounded

    log = TransformationLogEntry(
        kind="coarsen_coordinates",
        columns=[lat_column, lon_column],
        parameters={"decimals": decimals},
        rows_affected=rows_affected,
        cells_changed=cells_changed,
        records_suppressed=0,
        notes=f"Coordinates rounded to {decimals} decimal places.",
    )

    return TransformationResult(df=new_df, log=log)
