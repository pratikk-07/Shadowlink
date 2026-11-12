"""Metrics and analysis helpers for column profiling."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from shadowlink.profiler.models import ColumnKind, ColumnProfile


def detect_column_kind(series: pd.Series) -> ColumnKind:
    """Determine high-level statistical kind of a column."""
    if pd.api.types.is_bool_dtype(series.dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series.dtype):
        return "numeric"
    return "categorical"


def check_mixed_types(series: pd.Series) -> bool:
    """Check if a series contains non-null values of different Python types."""
    non_nulls = series.dropna()
    if len(non_nulls) <= 1:
        return False
    return bool(non_nulls.map(type).nunique() > 1)


def profile_series(series: pd.Series, col_name: str, total_rows: int) -> ColumnProfile:
    """Compute detailed profile metrics for a single pandas Series."""
    missing_count = int(series.isna().sum())
    non_missing_count = total_rows - missing_count

    if total_rows == 0:
        missing_rate: float | None = None
        distinct_count = 0
        uniqueness_ratio: float | None = None
    else:
        missing_rate = missing_count / total_rows
        # distinct non-missing count
        distinct_count = int(series.dropna().nunique())
        uniqueness_ratio = distinct_count / total_rows

    is_all_null = missing_count == total_rows and total_rows > 0
    # Constant means all non-missing values are identical, with 0 missing values
    is_constant = distinct_count == 1 and missing_count == 0 and total_rows > 0

    has_mixed_types = check_mixed_types(series)
    kind = detect_column_kind(series)

    numeric_summary: dict[str, float] | None = None
    categorical_frequencies: list[tuple[Any, int]] | None = None
    datetime_range: dict[str, str] | None = None

    if kind == "numeric" and non_missing_count > 0:
        numeric_series = pd.to_numeric(series.dropna(), errors="coerce").dropna()
        if not numeric_series.empty:
            std_val = (
                float(numeric_series.std(ddof=1)) if len(numeric_series) > 1 else 0.0
            )
            if np.isnan(std_val):
                std_val = 0.0
            numeric_summary = {
                "min": float(numeric_series.min()),
                "max": float(numeric_series.max()),
                "mean": float(numeric_series.mean()),
                "std": std_val,
                "25%": float(numeric_series.quantile(0.25)),
                "50%": float(numeric_series.median()),
                "75%": float(numeric_series.quantile(0.75)),
            }
    elif kind == "datetime" and non_missing_count > 0:
        dt_series = series.dropna()
        datetime_range = {
            "min": str(dt_series.min()),
            "max": str(dt_series.max()),
        }
    else:
        # Categorical or Boolean or mixed
        if non_missing_count > 0:
            top_counts = series.dropna().value_counts().head(5)
            categorical_frequencies = [
                (idx, int(cnt)) for idx, cnt in top_counts.items()
            ]

    return ColumnProfile(
        name=col_name,
        dtype=str(series.dtype),
        kind=kind,
        missing_count=missing_count,
        missing_rate=missing_rate,
        distinct_count=distinct_count,
        uniqueness_ratio=uniqueness_ratio,
        is_constant=is_constant,
        is_all_null=is_all_null,
        has_mixed_types=has_mixed_types,
        numeric_summary=numeric_summary,
        categorical_frequencies=categorical_frequencies,
        datetime_range=datetime_range,
    )
