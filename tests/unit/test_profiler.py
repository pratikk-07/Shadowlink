"""Unit tests for the Data Profiler module (Phase 1).

Covers:
- profile_dataframe on golden fixture A with exact hand-calculated assertions
- profile_csv on golden fixture A and fixture B
- missing_rate, distinct_count, uniqueness_ratio with [A, A, B, None, None]
- all-null columns, constant columns, mixed-type columns
- 0-row DataFrames (rates become None)
- duplicate row detection (keep='first' counting)
- validation checks (forbidden columns, duplicate columns, 0 columns, unhashable values)
- error handling for missing/empty/malformed files in profile_csv -> DatasetLoadError
- immutability (input DataFrame copy is identical before and after)
- JSON serialization and round-trip fidelity
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shadowlink.common.exceptions import DatasetLoadError, ValidationError
from shadowlink.profiler.models import DatasetProfile
from shadowlink.profiler.profiler import profile_csv, profile_dataframe

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")
FIXTURE_B_PATH = Path("tests/fixtures/tiny_people_b.csv")


class TestProfileFixtureA:
    """Exact hand-verified expectations for tiny_people_a.csv.

    8 rows, 3 columns:
    age (int): 20, 20, 21, 21, 21, 22, 22, 23 -> distinct = 4, uniq = 4/8 = 0.5
    city (str): Kolkata(3), Delhi(4), Mumbai(1) -> distinct = 3, uniq = 3/8 = 0.375
    course (str): CSE(5), ECE(3) -> distinct = 2, uniqueness = 2/8 = 0.25
    duplicates: rows 5 and 6 are both 22,Delhi,CSE -> duplicate_row_count = 1
    missing: 0 for all
    """

    def test_fixture_a_profile_dataframe(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        profile = profile_dataframe(df, dataset_name="fixture_a")

        assert profile.dataset_name == "fixture_a"
        assert profile.row_count == 8
        assert profile.column_count == 3
        assert profile.duplicate_row_count == 1
        assert profile.memory_bytes > 0
        assert len(profile.columns) == 3

        col_map = {col.name: col for col in profile.columns}
        assert set(col_map.keys()) == {"age", "city", "course"}

        # Age column
        age_col = col_map["age"]
        assert age_col.kind == "numeric"
        assert age_col.missing_count == 0
        assert age_col.missing_rate == pytest.approx(0.0)
        assert age_col.distinct_count == 4
        assert age_col.uniqueness_ratio == pytest.approx(0.5)
        assert not age_col.is_constant
        assert not age_col.is_all_null
        assert not age_col.has_mixed_types
        assert age_col.numeric_summary is not None
        assert age_col.numeric_summary["min"] == pytest.approx(20.0)
        assert age_col.numeric_summary["max"] == pytest.approx(23.0)

        # City column
        city_col = col_map["city"]
        assert city_col.kind == "categorical"
        assert city_col.missing_count == 0
        assert city_col.missing_rate == pytest.approx(0.0)
        assert city_col.distinct_count == 3
        assert city_col.uniqueness_ratio == pytest.approx(0.375)
        assert not city_col.is_constant
        assert not city_col.is_all_null
        assert city_col.categorical_frequencies is not None
        freq_dict = dict(city_col.categorical_frequencies)
        assert freq_dict["Delhi"] == 4
        assert freq_dict["Kolkata"] == 3
        assert freq_dict["Mumbai"] == 1

        # Course column
        course_col = col_map["course"]
        assert course_col.kind == "categorical"
        assert course_col.missing_count == 0
        assert course_col.missing_rate == pytest.approx(0.0)
        assert course_col.distinct_count == 2
        assert course_col.uniqueness_ratio == pytest.approx(0.25)
        assert not course_col.is_constant
        assert not course_col.is_all_null

    def test_fixture_a_profile_csv(self) -> None:
        profile = profile_csv(FIXTURE_A_PATH, dataset_name="custom_a")
        assert profile.dataset_name == "custom_a"
        assert profile.row_count == 8
        assert profile.duplicate_row_count == 1

    def test_fixture_a_profile_csv_default_name(self) -> None:
        profile = profile_csv(FIXTURE_A_PATH)
        assert profile.dataset_name == "tiny_people_a"


class TestProfileFixtureB:
    """Fixture B has spaces in headers: ' Age ', 'CITY', 'location', 'timestamp'."""

    def test_fixture_b_profile_csv(self) -> None:
        profile = profile_csv(FIXTURE_B_PATH, parse_dates=["timestamp"])
        assert profile.row_count == 5
        assert profile.column_count == 4
        col_names = [col.name for col in profile.columns]
        # Original column names preserved in ColumnProfile.name
        assert " Age " in col_names
        assert "CITY" in col_names
        assert "location" in col_names
        assert "timestamp" in col_names

        # Check timestamp was recognized/parsed as datetime
        ts_col = next(col for col in profile.columns if col.name == "timestamp")
        assert ts_col.kind == "datetime"
        assert ts_col.datetime_range is not None
        assert "2024-01-15" in ts_col.datetime_range["min"]
        assert "2024-01-19" in ts_col.datetime_range["max"]


class TestColumnMetricsEdgeCases:
    """Checks on missing_rate, distinct_count, uniqueness_ratio, edge values."""

    def test_sample_a_a_b_none_none(self) -> None:
        # [A, A, B, None, None] -> total rows = 5
        # non-null = 3, missing = 2 -> missing_rate = 2/5 = 0.4
        # distinct non-missing = 2 ('A', 'B') -> distinct_count = 2
        # uniqueness_ratio = 2 / 5 = 0.4
        df = pd.DataFrame({"col": ["A", "A", "B", None, None]})
        profile = profile_dataframe(df, dataset_name="test_missing")
        col = profile.columns[0]

        assert col.missing_count == 2
        assert col.missing_rate == pytest.approx(0.4)
        assert col.distinct_count == 2
        assert col.uniqueness_ratio == pytest.approx(0.4)
        assert not col.is_constant
        assert not col.is_all_null

    def test_all_null_column(self) -> None:
        df = pd.DataFrame({"empty_col": [None, np.nan, None]})
        profile = profile_dataframe(df)
        col = profile.columns[0]

        assert col.missing_count == 3
        assert col.missing_rate == pytest.approx(1.0)
        assert col.distinct_count == 0
        assert col.uniqueness_ratio == pytest.approx(0.0)
        assert col.is_all_null
        assert not col.is_constant

    def test_constant_column(self) -> None:
        df = pd.DataFrame({"same": ["fixed", "fixed", "fixed"]})
        profile = profile_dataframe(df)
        col = profile.columns[0]

        assert col.missing_count == 0
        assert col.missing_rate == pytest.approx(0.0)
        assert col.distinct_count == 1
        assert col.uniqueness_ratio == pytest.approx(1 / 3)
        assert col.is_constant
        assert not col.is_all_null

    def test_constant_with_nulls_is_not_constant(self) -> None:
        # A column with ["x", None] has 1 distinct non-null, but nulls are present
        df = pd.DataFrame({"semi": ["x", None, "x"]})
        profile = profile_dataframe(df)
        col = profile.columns[0]
        # Policy: is_constant is True only when all values are identical
        # and no missing values exist.
        assert not col.is_constant
        assert col.distinct_count == 1

    def test_mixed_types_column(self) -> None:
        df = pd.DataFrame({"mixed": [10, "ten", 10.5, True]})
        profile = profile_dataframe(df)
        col = profile.columns[0]
        assert col.has_mixed_types

    def test_empty_dataframe_zero_rows(self) -> None:
        df = pd.DataFrame(columns=["col1", "col2"])
        profile = profile_dataframe(df)

        assert profile.row_count == 0
        assert profile.column_count == 2
        assert profile.duplicate_row_count == 0
        for col in profile.columns:
            assert col.missing_count == 0
            assert col.missing_rate is None
            assert col.distinct_count == 0
            assert col.uniqueness_ratio is None
            assert not col.is_constant
            assert not col.is_all_null

    def test_boolean_column(self) -> None:
        df = pd.DataFrame({"flag": [True, False, True, True]})
        profile = profile_dataframe(df)
        col = profile.columns[0]
        assert col.kind == "boolean"
        assert col.distinct_count == 2


class TestValidationAndErrorHandling:
    """Verify input validation and custom exceptions."""

    def test_forbidden_column_raises_validation_error(self) -> None:
        df = pd.DataFrame({"age": [20], "ground_truth": [101]})
        with pytest.raises(ValidationError, match="forbidden column"):
            profile_dataframe(df)

    def test_duplicate_columns_raises_validation_error(self) -> None:
        df = pd.DataFrame([[20, 20]], columns=["age", "age"])
        with pytest.raises(ValidationError, match="duplicate column"):
            profile_dataframe(df)

    def test_zero_columns_raises_validation_error(self) -> None:
        df = pd.DataFrame()
        with pytest.raises(ValidationError, match="zero columns"):
            profile_dataframe(df)

    def test_unhashable_cell_raises_validation_error(self) -> None:
        df = pd.DataFrame({"col": [[1, 2], [3, 4]]})
        with pytest.raises(ValidationError, match="unhashable"):
            profile_dataframe(df)

    def test_profile_csv_missing_file_raises_dataset_load_error(self) -> None:
        with pytest.raises(DatasetLoadError, match="File not found"):
            profile_csv("tests/fixtures/non_existent_file.csv")

    def test_profile_csv_empty_file_raises_dataset_load_error(
        self, tmp_path: Path
    ) -> None:
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("", encoding="utf-8")
        with pytest.raises(DatasetLoadError, match="empty"):
            profile_csv(empty_csv)

    def test_profile_csv_directory_path_raises_dataset_load_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(DatasetLoadError, match="not a file"):
            profile_csv(tmp_path)


class TestImmutabilityAndSerialization:
    """Verify DataFrame is not mutated and serialization works."""

    def test_input_dataframe_not_mutated(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        df_copy = df.copy(deep=True)
        _ = profile_dataframe(df, dataset_name="fixture_a")
        pd.testing.assert_frame_equal(df, df_copy)

    def test_json_round_trip(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        profile = profile_dataframe(df, dataset_name="round_trip")

        json_str = profile.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["dataset_name"] == "round_trip"
        assert parsed["row_count"] == 8
        assert parsed["column_count"] == 3

        reconstructed = DatasetProfile.from_json(json_str)
        assert reconstructed.dataset_name == profile.dataset_name
        assert reconstructed.row_count == profile.row_count
        assert reconstructed.column_count == profile.column_count
        assert reconstructed.duplicate_row_count == profile.duplicate_row_count
        assert len(reconstructed.columns) == len(profile.columns)

        for col_orig, col_recon in zip(profile.columns, reconstructed.columns):
            assert col_orig.name == col_recon.name
            assert col_orig.dtype == col_recon.dtype
            assert col_orig.kind == col_recon.kind
            assert col_orig.missing_count == col_recon.missing_count
            assert col_orig.missing_rate == col_recon.missing_rate
            assert col_orig.distinct_count == col_recon.distinct_count
            assert col_orig.uniqueness_ratio == col_recon.uniqueness_ratio
            assert col_orig.is_constant == col_recon.is_constant
            assert col_orig.is_all_null == col_recon.is_all_null
            assert col_orig.has_mixed_types == col_recon.has_mixed_types
