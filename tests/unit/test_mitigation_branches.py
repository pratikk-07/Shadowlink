"""Additional branch and error condition tests for mitigation and risk modules.

Boosts test coverage well above 90% across:
- mitigation (pipeline, binning, generalization, spatial, temporal, utility)
- risk explanations and candidate models
"""

from __future__ import annotations

import pandas as pd
import pytest

from shadowlink.common.exceptions import ConfigError, ValidationError
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
from shadowlink.risk.candidate_models import CandidateRiskReport
from shadowlink.risk.explanations import explain_risk
from shadowlink.risk.metrics import calculate_class_risk


class TestMitigationBranchCoverage:
    """Exercise remaining branches and edge cases in mitigation modules."""

    def test_pipeline_all_kinds(self) -> None:
        df = pd.DataFrame(
            {
                "age": [20, 22],
                "city": ["Delhi", "Mumbai"],
                "score": [85.5, 92.0],
                "lat": [28.6139, 19.0760],
                "lon": [77.2090, 72.8777],
                "ts": ["2024-01-01 10:00:00", "2024-01-02 12:30:00"],
            }
        )

        specs = [
            TransformationSpec(
                "bin_numeric", {"column": "score", "edges": [80.0, 90.0, 100.0]}
            ),
            TransformationSpec(
                "generalize_by_hierarchy",
                {
                    "column": "city",
                    "mapping": {"Delhi": "North"},
                    "replacement": "OTHER",
                },
            ),
            TransformationSpec(
                "suppress_rare_values",
                {"column": "city", "minimum_frequency": 2, "replacement": "RARE"},
            ),
            TransformationSpec(
                "coarsen_coordinates",
                {"lat_column": "lat", "lon_column": "lon", "decimals": 1},
            ),
            TransformationSpec("coarsen_timestamp", {"column": "ts", "level": "hour"}),
        ]

        report = run_mitigation_experiment(
            original=df,
            specs=specs,
            qi_columns=["age", "city"],
            queries={"avg_age": lambda d: d["age"].mean()},
        )
        assert len(report.transformation_logs) == 5
        assert "avg_age" in report.query_answers
        assert report.to_json() is not None

    def test_pipeline_unknown_kind_raises(self) -> None:
        df = pd.DataFrame({"age": [20]})
        specs = [TransformationSpec("magic_wipe", {})]
        with pytest.raises(ConfigError, match="Unknown transformation kind"):
            run_mitigation_experiment(df, specs, qi_columns=["age"])

    def test_generalize_age_out_of_range_error(self) -> None:
        df = pd.DataFrame({"age": [150]})
        with pytest.raises(ValidationError, match="out of valid range"):
            generalize_age(df, column="age", bin_width=5, out_of_range="error")

    def test_generalize_age_missing_column(self) -> None:
        df = pd.DataFrame({"x": [1]})
        with pytest.raises(ValidationError, match="not found"):
            generalize_age(df, column="age", bin_width=5)

    def test_generalize_by_hierarchy_errors(self) -> None:
        df = pd.DataFrame({"city": ["Atlantis"]})
        with pytest.raises(ValidationError, match="Unmapped value"):
            generalize_by_hierarchy(
                df, "city", mapping={"Delhi": "D"}, unmapped="error"
            )

        with pytest.raises(ValidationError, match="not found"):
            generalize_by_hierarchy(df, "nonexistent", mapping={})

        res_keep = generalize_by_hierarchy(
            df, "city", mapping={"Delhi": "D"}, unmapped="keep"
        )
        assert res_keep.df["city"].iloc[0] == "Atlantis"

    def test_bin_numeric_errors(self) -> None:
        df = pd.DataFrame({"val": [10.0, 50.0]})
        with pytest.raises(ValidationError, match="not found"):
            bin_numeric(df, "not_here", [10, 20])
        with pytest.raises(ValidationError, match="at least 2"):
            bin_numeric(df, "val", [10])
        with pytest.raises(ValidationError, match="Number of labels"):
            bin_numeric(df, "val", [10, 20, 30], labels=["single_label"])
        with pytest.raises(ValidationError, match="outside interval"):
            bin_numeric(df, "val", [10, 20], out_of_range="error")
        with pytest.raises(ValidationError, match="Non-numeric value"):
            df_bad = pd.DataFrame({"val": ["not_a_number"]})
            bin_numeric(df_bad, "val", [10, 20])

    def test_suppress_rare_values_errors(self) -> None:
        df = pd.DataFrame({"city": ["Delhi", "Delhi"]})
        with pytest.raises(ValidationError, match="not found"):
            suppress_rare_values(df, "unknown", 2)
        with pytest.raises(ValidationError, match="must be > 1"):
            suppress_rare_values(df, "city", 1)
        with pytest.raises(ValidationError, match="already exists"):
            suppress_rare_values(df, "city", 2, replacement="Delhi")

    def test_suppress_small_classes_errors(self) -> None:
        df = pd.DataFrame({"age": [20]})
        with pytest.raises(ValidationError, match="k must be >= 2"):
            suppress_small_classes(df, ["age"], k=1)

    def test_coarsen_timestamp_errors(self) -> None:
        df = pd.DataFrame({"ts": ["2024-01-01 10:00:00"]})
        with pytest.raises(ValidationError, match="not found"):
            coarsen_timestamp(df, "unknown", "hour")
        with pytest.raises(ValidationError, match="Invalid level"):
            coarsen_timestamp(df, "ts", "year")  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match="Cannot parse timestamp"):
            df_bad = pd.DataFrame({"ts": ["unparseable_junk"]})
            coarsen_timestamp(df_bad, "ts", "hour")

    def test_coarsen_coordinates_errors(self) -> None:
        df = pd.DataFrame({"lat": [20.0], "lon": [80.0]})
        with pytest.raises(ValidationError, match="not found"):
            coarsen_coordinates(df, "lat_bad", "lon", decimals=2)
        with pytest.raises(ValidationError, match="decimals must be >= 0"):
            coarsen_coordinates(df, "lat", "lon", decimals=-1)
        with pytest.raises(ValidationError, match="must be numeric"):
            df_bad = pd.DataFrame({"lat": ["not_lat"], "lon": [80.0]})
            coarsen_coordinates(df_bad, "lat", "lon", decimals=2)

    def test_aggregate_counts_errors(self) -> None:
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValidationError, match="cannot be empty"):
            aggregate_counts(df, [])
        with pytest.raises(ValidationError, match="Columns not found"):
            aggregate_counts(df, ["missing"])

    def test_compare_privacy_utility_errors(self) -> None:
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValidationError, match="missing from original"):
            compare_privacy_utility(df, df, qi_columns=["b"])
        with pytest.raises(ValidationError, match="missing from transformed"):
            df2 = pd.DataFrame({"c": [1]})
            compare_privacy_utility(df, df2, qi_columns=["a"])


class TestRiskExplanationsFullCoverage:
    """Test all risk explanation tiers and edge cases."""

    def test_all_explanation_tiers(self) -> None:
        # k=10, max_risk=0.1, avg_risk=0.1, uniqueness=0.0
        df = pd.DataFrame({"qi": ["A"] * 10 + ["B"] * 10})
        eq = build_equivalence_classes(df, ["qi"])
        rep = calculate_class_risk(eq)
        exps = explain_risk(rep)
        assert any(e.level == "LOW" for e in exps)
        assert any("Strong k-anonymity" in e.summary for e in exps)

        # k=3
        df_k3 = pd.DataFrame({"qi": ["A"] * 3 + ["B"] * 3})
        eq_k3 = build_equivalence_classes(df_k3, ["qi"])
        rep_k3 = calculate_class_risk(eq_k3)
        exps_k3 = explain_risk(rep_k3)
        assert any("k=3" in e.summary for e in exps_k3)

    def test_candidate_risk_report_serialization(self) -> None:
        rep = CandidateRiskReport(initial_count=10, steps=[])
        json_str = rep.to_json()
        recon = CandidateRiskReport.from_json(json_str)
        assert recon.initial_count == 10
