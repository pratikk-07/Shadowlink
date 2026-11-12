"""Unit tests for the Mitigation Engine (Phase 5).

Covers:
- generalize_age on Fixture A with width=5, base=0:
    all ages (20, 21, 22, 23) map to "20-24"
    QI [age, city] on generalized frame:
      classes: (20-24, Kolkata)->3, (20-24, Delhi)->4, (20-24, Mumbai)->1
      k = 1, singleton_record_count = 1 (1/8 = 0.125)
      average_risk = 3/8 = 0.375
      DM = 3^2 + 4^2 + 1^2 = 9 + 16 + 1 = 26 (increased from 14!)
- suppress_small_classes(k=2) on the generalized frame:
    removes the Mumbai record (class of size 1)
    N = 7 records remain
    classes: Kolkata->3, Delhi->4
    k = 3
    singleton_record_count = 0, average_risk = 2/7, max_risk = 1/3
    DM = 9 + 16 = 25
    records_suppressed = 1 of 8
- suppress_rare_values(city, min_freq=2):
    Kolkata=3, Delhi=4, Mumbai=1 -> Mumbai is replaced with 'SUPPRESSED'
    cells_changed = 1 of 8
- bin_numeric boundary and interval checks
- coarsen_timestamp with minute, hour, day (verifying no-date-shift at 23:59:59)
- coarsen_coordinates with decimal precision
- generalize_by_hierarchy lookup mapping
- aggregate_counts count table
- compare_privacy_utility and pipeline.run_mitigation_experiment
- Regression test: DM can increase while uniqueness decreases
- Immutability check: caller DataFrame is never mutated
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shadowlink.common.exceptions import ValidationError
from shadowlink.mitigation.aggregation import aggregate_counts
from shadowlink.mitigation.binning import bin_numeric
from shadowlink.mitigation.generalization import (
    generalize_age,
    generalize_by_hierarchy,
)
from shadowlink.mitigation.models import TransformationSpec
from shadowlink.mitigation.pipeline import run_mitigation_experiment
from shadowlink.mitigation.spatial import coarsen_coordinates
from shadowlink.mitigation.suppression import (
    suppress_rare_values,
    suppress_small_classes,
)
from shadowlink.mitigation.temporal import coarsen_timestamp
from shadowlink.mitigation.utility import compare_privacy_utility
from shadowlink.qi_analyser.equivalence import build_equivalence_classes

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")


class TestFixtureAGoldenMitigationChain:
    """Hand-verified golden mitigation progression on tiny_people_a.csv."""

    def test_golden_generalize_age(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        df_copy = df.copy(deep=True)

        res = generalize_age(df, column="age", bin_width=5, base=0)
        # Verify original was not mutated
        pd.testing.assert_frame_equal(df, df_copy)

        gen_df = res.df
        assert res.log.kind == "generalize_age"
        assert res.log.rows_affected == 8
        assert res.log.cells_changed == 8

        # All ages in Fixture A (20, 21, 22, 23) belong to [20, 25) -> "20-24"
        assert (gen_df["age"] == "20-24").all()

        # Equivalence classes on QI [age, city]
        eq = build_equivalence_classes(gen_df, qi_columns=["age", "city"])
        assert eq.total_records == 8
        assert eq.class_sizes == [4, 3, 1]  # Delhi: 4, Kolkata: 3, Mumbai: 1
        assert eq.num_classes == 3
        assert eq.k == 1
        assert eq.singleton_record_count == 1
        assert eq.singleton_record_proportion == pytest.approx(1 / 8)

        # DM = 4^2 + 3^2 + 1^2 = 16 + 9 + 1 = 26
        # Note: DM increased from 14 to 26 because classes grew larger!
        dm = sum(s**2 for s in eq.class_sizes)
        assert dm == 26

    def test_golden_suppress_small_classes_after_generalization(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        gen_res = generalize_age(df, column="age", bin_width=5, base=0)

        # Now apply suppress_small_classes with k=2 on QI [age, city]
        sup_res = suppress_small_classes(gen_res.df, qi_columns=["age", "city"], k=2)
        sup_df = sup_res.df

        # Mumbai record had class size 1 (< 2), so it is suppressed
        assert sup_res.log.records_suppressed == 1
        assert len(sup_df) == 7
        assert "Mumbai" not in sup_df["city"].values

        # Equivalence classes on remaining 7 records
        eq = build_equivalence_classes(sup_df, qi_columns=["age", "city"])
        assert eq.total_records == 7
        assert eq.records_analysed == 7
        assert eq.class_sizes == [4, 3]  # Delhi: 4, Kolkata: 3
        assert eq.num_classes == 2
        assert eq.k == 3  # min(4, 3) = 3
        assert eq.singleton_record_count == 0
        assert eq.singleton_record_proportion == pytest.approx(0.0)

        # DM = 4^2 + 3^2 = 16 + 9 = 25
        dm = sum(s**2 for s in eq.class_sizes)
        assert dm == 25

    def test_golden_suppress_rare_values_city(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        # Kolkata=3, Delhi=4, Mumbai=1
        res = suppress_rare_values(df, column="city", minimum_frequency=2)
        trans_df = res.df

        assert res.log.cells_changed == 1
        assert (trans_df["city"] == "SUPPRESSED").sum() == 1
        # The single Mumbai record is replaced with SUPPRESSED
        mumbai_idx = df.index[df["city"] == "Mumbai"].tolist()[0]
        assert trans_df.loc[mumbai_idx, "city"] == "SUPPRESSED"


class TestGeneralizationBoundariesAndPolicies:
    """Edge cases for age generalization and hierarchy lookups."""

    def test_generalize_age_boundary_values(self) -> None:
        # width=5, base=0: 24 -> "20-24", 25 -> "25-29"
        df = pd.DataFrame({"age": [24, 25, 29, 30]})
        res = generalize_age(df, column="age", bin_width=5, base=0)
        expected = ["20-24", "25-29", "25-29", "30-34"]
        assert list(res.df["age"]) == expected

    def test_generalize_age_missing_stays_missing(self) -> None:
        df = pd.DataFrame({"age": [20, None, np.nan]})
        res = generalize_age(df, column="age", bin_width=5)
        assert res.df["age"].iloc[0] == "20-24"
        assert pd.isna(res.df["age"].iloc[1])
        assert pd.isna(res.df["age"].iloc[2])

    def test_generalize_age_invalid_width_raises(self) -> None:
        df = pd.DataFrame({"age": [20]})
        with pytest.raises(ValidationError, match="bin_width must be > 0"):
            generalize_age(df, column="age", bin_width=0)

    def test_generalize_age_non_integer_raises(self) -> None:
        df = pd.DataFrame({"age": [20.5, 21.0]})
        with pytest.raises(ValidationError, match="integer-valued ages"):
            generalize_age(df, column="age", bin_width=5)

    def test_generalize_by_hierarchy(self) -> None:
        df = pd.DataFrame({"city": ["Kolkata", "Delhi", "UnknownCity"]})
        mapping = {"Kolkata": "East", "Delhi": "North"}
        res = generalize_by_hierarchy(
            df, column="city", mapping=mapping, unmapped="suppress"
        )
        assert list(res.df["city"]) == ["East", "North", "SUPPRESSED"]


class TestBinningNumeric:
    """Binning continuous numeric values into half-open intervals [a, b)."""

    def test_bin_numeric_edges_and_labels(self) -> None:
        df = pd.DataFrame({"val": [10.0, 15.5, 20.0, 29.9, 30.0]})
        edges = [10.0, 20.0, 30.0]
        # Intervals: [10.0, 20.0), [20.0, 30.0)
        res = bin_numeric(
            df,
            column="val",
            edges=edges,
            labels=["low", "high"],
            out_of_range="suppress",
        )
        assert list(res.df["val"]) == ["low", "low", "high", "high", "SUPPRESSED"]

    def test_bin_numeric_unsorted_edges_raises(self) -> None:
        df = pd.DataFrame({"val": [10]})
        with pytest.raises(ValidationError, match="strictly increasing"):
            bin_numeric(df, column="val", edges=[20, 10])


class TestTemporalAndSpatialCoarsening:
    """Coarsening timestamp and coordinate attributes."""

    def test_coarsen_timestamp_levels_and_no_date_shift(self) -> None:
        # 23:59:59 at level="day" must NOT shift to the next date!
        df = pd.DataFrame({"ts": ["2024-03-15 23:59:59", "2024-03-15 14:35:12"]})
        # Day level
        res_day = coarsen_timestamp(df, column="ts", level="day")
        assert list(res_day.df["ts"]) == ["2024-03-15 00:00:00", "2024-03-15 00:00:00"]

        # Hour level
        res_hr = coarsen_timestamp(df, column="ts", level="hour")
        assert list(res_hr.df["ts"]) == ["2024-03-15 23:00:00", "2024-03-15 14:00:00"]

        # Minute level
        res_min = coarsen_timestamp(df, column="ts", level="minute")
        assert list(res_min.df["ts"]) == ["2024-03-15 23:59:00", "2024-03-15 14:35:00"]

    def test_coarsen_coordinates(self) -> None:
        df = pd.DataFrame(
            {
                "lat": [22.57264, 28.61393],
                "lon": [88.36389, 77.20902],
            }
        )
        res = coarsen_coordinates(df, lat_column="lat", lon_column="lon", decimals=2)
        assert list(res.df["lat"]) == [22.57, 28.61]
        assert list(res.df["lon"]) == [88.36, 77.21]


class TestAggregationAndPrivacyUtilityComparison:
    """Aggregation table and before/after mitigation report."""

    def test_aggregate_counts(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        agg_df = aggregate_counts(df, group_columns=["city", "course"])
        # Should return a table with count column
        assert "count" in agg_df.columns
        assert agg_df["count"].sum() == 8

    def test_compare_privacy_utility_and_dm_regression(self) -> None:
        """Verify regression where DM increases as risk drops."""
        orig_df = pd.read_csv(FIXTURE_A_PATH)
        gen_res = generalize_age(orig_df, column="age", bin_width=5, base=0)

        report = compare_privacy_utility(
            original=orig_df,
            transformed=gen_res.df,
            qi_columns=["age", "city"],
        )

        assert report.before["k"] == 1
        assert report.after["k"] == 1
        assert report.before["uniqueness"] == pytest.approx(0.25)
        assert report.after["uniqueness"] == pytest.approx(0.125)  # Dropped!

        # DM increased from 14 to 26
        assert report.before["discernibility_metric"] == 14
        assert report.after["discernibility_metric"] == 26

    def test_run_mitigation_experiment_pipeline(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        specs = [
            TransformationSpec(
                kind="generalize_age",
                parameters={"column": "age", "bin_width": 5, "base": 0},
            ),
            TransformationSpec(
                kind="suppress_small_classes",
                parameters={"qi_columns": ["age", "city"], "k": 2},
            ),
        ]

        report = run_mitigation_experiment(df, specs=specs, qi_columns=["age", "city"])
        assert report.before["k"] == 1
        assert report.after["k"] == 3
        assert report.after["record_count"] == 7
        assert report.suppression_fraction == pytest.approx(1 / 8)
        assert len(report.transformation_logs) == 2
