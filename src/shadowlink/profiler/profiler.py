"""Data Profiler API for tabular datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import DatasetLoadError
from shadowlink.common.validation import (
    validate_has_columns,
    validate_hashable_values,
    validate_no_duplicate_columns,
    validate_no_forbidden_columns,
)
from shadowlink.profiler.metrics import profile_series
from shadowlink.profiler.models import ColumnProfile, DatasetProfile


def profile_dataframe(
    df: pd.DataFrame, dataset_name: str = "dataset"
) -> DatasetProfile:
    """Generate a comprehensive statistical profile of a DataFrame.

    Validates schema defensive invariants and never mutates caller DataFrame.

    Parameters
    ----------
    df:
        Input pandas DataFrame to profile.
    dataset_name:
        User-provided or generated name for the dataset.

    Returns
    -------
    DatasetProfile
        Immutable profile report containing dataset-level and column-level metrics.
    """
    # Defensive checks
    validate_no_forbidden_columns(df)
    validate_no_duplicate_columns(df)
    validate_has_columns(df)
    validate_hashable_values(df)

    row_count = len(df)
    column_count = len(df.columns)

    # Calculate duplicate rows (keep="first" policy)
    if row_count > 0:
        duplicate_row_count = int(df.duplicated(keep="first").sum())
    else:
        duplicate_row_count = 0

    memory_bytes = int(df.memory_usage(deep=True).sum())

    column_profiles: list[ColumnProfile] = []
    for col in df.columns:
        col_name = str(col)
        series = df[col]
        col_prof = profile_series(series, col_name=col_name, total_rows=row_count)
        column_profiles.append(col_prof)

    return DatasetProfile(
        dataset_name=dataset_name,
        row_count=row_count,
        column_count=column_count,
        columns=column_profiles,
        duplicate_row_count=duplicate_row_count,
        memory_bytes=memory_bytes,
    )


def profile_csv(
    path: str | Path,
    dataset_name: str | None = None,
    parse_dates: Sequence[str] | None = None,
) -> DatasetProfile:
    """Read a CSV file and return its DatasetProfile.

    Parameters
    ----------
    path:
        Path to the CSV file.
    dataset_name:
        Optional name. If not provided, filename stem is used.
    parse_dates:
        Optional list of column names to parse as datetime objects.

    Returns
    -------
    DatasetProfile
    """
    file_path = Path(path)
    if not file_path.exists():
        raise DatasetLoadError(
            f"File not found: {file_path}. Ensure path is valid and exists."
        )
    if not file_path.is_file():
        raise DatasetLoadError(f"Specified path is not a file: {file_path}.")

    try:
        # Check if empty (size == 0)
        if file_path.stat().st_size == 0:
            raise DatasetLoadError(f"Dataset file is empty (0 bytes): {file_path}.")

        parse_dates_arg = list(parse_dates) if parse_dates else False
        df = pd.read_csv(file_path, parse_dates=parse_dates_arg)
    except DatasetLoadError:
        raise
    except Exception as exc:
        raise DatasetLoadError(
            f"Failed to read or parse CSV file '{file_path}': {exc}."
        ) from exc

    resolved_name = dataset_name if dataset_name is not None else file_path.stem
    return profile_dataframe(df, dataset_name=resolved_name)
