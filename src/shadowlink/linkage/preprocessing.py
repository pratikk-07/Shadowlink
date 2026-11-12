"""Data preprocessing and standardization routines for record linkage."""

from __future__ import annotations

import datetime
import re
from typing import Sequence

import pandas as pd

from shadowlink.common.normalization import normalize_column_name
from shadowlink.common.validation import validate_no_forbidden_columns


def _is_none_or_na(val: object) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))  # type: ignore[call-overload,arg-type]
    except Exception:
        return False


def standardize_text(val: object) -> str | None:
    """Standardize a string value: strip, lowercase, collapse whitespace."""
    if _is_none_or_na(val):
        return None
    s = re.sub(r"\s+", " ", str(val).strip().lower())
    if not s:
        return None
    return s


def parse_datetime_safe(val: object) -> datetime.datetime | None:
    """Safely parse a datetime object or ISO string."""
    if _is_none_or_na(val):
        return None
    if isinstance(val, datetime.datetime):
        return val
    try:
        s = str(val).strip()
        # Handle standard ISO formats
        return datetime.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def preprocess_linkage_frame(
    df: pd.DataFrame,
    text_columns: Sequence[str] | None = None,
    datetime_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Standardize column names and text/datetime columns for linkage.

    Never mutates caller's DataFrame.
    """
    validate_no_forbidden_columns(df)
    clean_df = df.copy(deep=True)

    # Normalize column names
    clean_df.columns = [normalize_column_name(c) for c in clean_df.columns]

    if text_columns:
        for col in text_columns:
            norm_col = normalize_column_name(col)
            if norm_col in clean_df.columns:
                clean_df[norm_col] = clean_df[norm_col].map(standardize_text)

    if datetime_columns:
        for col in datetime_columns:
            norm_col = normalize_column_name(col)
            if norm_col in clean_df.columns:
                clean_df[norm_col] = clean_df[norm_col].map(parse_datetime_safe)

    return clean_df
