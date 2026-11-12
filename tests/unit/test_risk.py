"""Unit tests for the Risk Engine (Phase 3).

Hand-verified test oracles and invariants:
- Fixture A on QI [age, city]:
    k = 1
    max_class_risk = 1 / 1 = 1.0
    average_class_risk = 5 / 8 = 0.625
    uniqueness = 2 / 8 = 0.25
- Fixture A on QI [age, city, course]:
    k = 1
    max_class_risk = 1.0
    average_class_risk = 7 / 8 = 0.875
    uniqueness = 6 / 8 = 0.75
- Sizes [1, 2, 2] on 5 records:
    record risks: [1.0, 0.5, 0.5, 0.5, 0.5]
    max_class_risk = 1.0
    average_class_risk = 3 / 5 = 0.6
- Sizes [2, 3] on 5 records:
    max_class_risk = 1 / 2 = 0.5
    average_class_risk = 2 / 5 = 0.4
- Mathematical proof test:
    mean(per_record_risk) == num_classes / records_analysed on seeded random data
- Invariant tests:
    - Every RiskMetric must have non-empty denominator, formula, assumption
    - Assumption text must explicitly mention "prosecutor"
    - No metric or dict key named 'composite', 'overall', 'total_score'
    - Zero records handle gracefully with None values, no division by zero.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.explanations import explain_risk
from shadowlink.risk.metrics import calculate_class_risk
from shadowlink.risk.models import RiskReport

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")


class TestFixtureARiskCalculations:
    """Exact hand-verified expectations on tiny_people_a.csv."""

    def test_fixture_a_age_city_risk(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        eq = build_equivalence_classes(df, qi_columns=["age", "city"])
        report = calculate_class_risk(eq)

        metric_map = {m.name: m for m in report.metrics}
        assert set(metric_map.keys()) == {
            "k_anonymity",
            "max_class_risk",
            "average_class_risk",
            "uniqueness",
            "discernibility_metric",
        }

        # k = 1
        assert metric_map["k_anonymity"].value == pytest.approx(1.0)

        # max_class_risk = 1 / 1 = 1.0
        assert metric_map["max_class_risk"].value == pytest.approx(1.0)
        assert metric_map["max_class_risk"].denominator == "k"

        # average_class_risk = 5 / 8 = 0.625
        assert metric_map["average_class_risk"].value == pytest.approx(0.625)
        assert metric_map["average_class_risk"].denominator == "records_analysed"

        # uniqueness = 2 / 8 = 0.25
        assert metric_map["uniqueness"].value == pytest.approx(0.25)
        assert metric_map["uniqueness"].denominator == "records_analysed"

        # discernibility_metric = 14
        assert metric_map["discernibility_metric"].value == pytest.approx(14.0)

        # Per-record risks check
        assert len(report.per_record_risk) == 8
        # Kolkata records (rows 0, 1) in class of 2 -> 1/2 = 0.5
        # Kolkata record (row 2) in class of 1 -> 1/1 = 1.0
        # Delhi records (rows 3, 4) in class of 2 -> 1/2 = 0.5
        # Delhi records (rows 5, 6) in class of 2 -> 1/2 = 0.5
        # Mumbai record (row 7) in class of 1 -> 1/1 = 1.0
        expected_record_risks = [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0]
        assert list(report.per_record_risk) == pytest.approx(expected_record_risks)

        # Explanations
        explanations = explain_risk(report)
        assert len(explanations) == len(report.metrics)
        high_or_crit = [e for e in explanations if e.level in ("HIGH", "CRITICAL")]
        # Since k=1 and uniqueness=0.25, high risk should be flagged
        assert len(high_or_crit) > 0

    def test_fixture_a_age_city_course_risk(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        eq = build_equivalence_classes(df, qi_columns=["age", "city", "course"])
        report = calculate_class_risk(eq)
        metric_map = {m.name: m for m in report.metrics}

        assert metric_map["k_anonymity"].value == pytest.approx(1.0)
        assert metric_map["max_class_risk"].value == pytest.approx(1.0)
        assert metric_map["average_class_risk"].value == pytest.approx(7 / 8)
        assert metric_map["uniqueness"].value == pytest.approx(6 / 8)
        assert metric_map["discernibility_metric"].value == pytest.approx(10.0)


class TestHandCalculatedScenarios:
    """Exact manual calculations on controlled equivalence class distributions."""

    def test_sizes_1_2_2(self) -> None:
        # 5 records: classes of size 1, 2, 2
        df = pd.DataFrame({"qi": ["A", "B", "B", "C", "C"]})
        eq = build_equivalence_classes(df, qi_columns=["qi"])
        report = calculate_class_risk(eq)
        metric_map = {m.name: m for m in report.metrics}

        assert metric_map["max_class_risk"].value == pytest.approx(1.0)
        assert metric_map["average_class_risk"].value == pytest.approx(3 / 5)
        assert metric_map["uniqueness"].value == pytest.approx(1 / 5)

        # Per record risk: [1.0, 0.5, 0.5, 0.5, 0.5]
        expected_risks = [1.0, 0.5, 0.5, 0.5, 0.5]
        assert list(report.per_record_risk) == pytest.approx(expected_risks)
        assert report.per_record_risk.mean() == pytest.approx(3 / 5)

    def test_sizes_2_3(self) -> None:
        # 5 records: classes of size 2, 3
        df = pd.DataFrame({"qi": ["A", "A", "B", "B", "B"]})
        eq = build_equivalence_classes(df, qi_columns=["qi"])
        report = calculate_class_risk(eq)
        metric_map = {m.name: m for m in report.metrics}

        assert metric_map["k_anonymity"].value == pytest.approx(2.0)
        assert metric_map["max_class_risk"].value == pytest.approx(0.5)
        assert metric_map["average_class_risk"].value == pytest.approx(2 / 5)
        assert metric_map["uniqueness"].value == pytest.approx(0.0)
        assert report.per_record_risk.mean() == pytest.approx(2 / 5)


class TestRiskInvariantsAndNonNegotiables:
    """Verification of Non-Negotiable Rule R3 and mathematical identities."""

    def test_no_composite_score_exists(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        eq = build_equivalence_classes(df, qi_columns=["age", "city"])
        report = calculate_class_risk(eq)

        # Ensure no composite metric exists in report.metrics
        forbidden_substrings = [
            "composite",
            "overall",
            "total_score",
            "aggregate_score",
            "risk_score",
        ]
        for m in report.metrics:
            m_name = m.name.lower()
            for bad_str in forbidden_substrings:
                assert bad_str not in m_name, f"Forbidden metric name found: {m.name}"

        # Ensure no composite key exists in to_dict / to_json
        report_dict = report.to_dict()
        for k in report_dict.keys():
            for bad_str in forbidden_substrings:
                assert bad_str not in k.lower(), f"Forbidden dictionary key: {k}"

    def test_every_metric_has_required_metadata(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        eq = build_equivalence_classes(df, qi_columns=["age", "city"])
        report = calculate_class_risk(eq)

        for m in report.metrics:
            assert m.name != ""
            assert m.formula != ""
            assert m.denominator != ""
            assert m.assumption != ""
            assert m.source_module != ""
            assert m.explanation != ""
            # Must explicitly document prosecutor model
            assert "prosecutor" in m.assumption.lower(), (
                f"Metric {m.name} assumption must specify prosecutor model"
            )

    @pytest.mark.parametrize("seed", [10, 55, 999])
    def test_mean_per_record_risk_equals_average_class_risk(self, seed: int) -> None:
        """Mathematical theorem: (1/n) * sum_{i=1}^n (1 / f_i) == num_classes / n."""
        rng = np.random.default_rng(seed)
        n = 120
        df = pd.DataFrame(
            {
                "age": rng.integers(18, 30, size=n),
                "city": rng.choice(["Delhi", "Mumbai", "Kolkata", "Chennai"], size=n),
            }
        )
        eq = build_equivalence_classes(df, qi_columns=["age", "city"])
        report = calculate_class_risk(eq)

        mean_rec_risk = float(report.per_record_risk.mean())
        avg_class_metric = next(
            m.value for m in report.metrics if m.name == "average_class_risk"
        )
        assert avg_class_metric is not None
        assert mean_rec_risk == pytest.approx(avg_class_metric)
        assert mean_rec_risk == pytest.approx(eq.num_classes / eq.records_analysed)

    def test_zero_records_dataframe_risk(self) -> None:
        df = pd.DataFrame(columns=["age", "city"])
        eq = build_equivalence_classes(df, qi_columns=["age", "city"])
        report = calculate_class_risk(eq)

        for m in report.metrics:
            if m.name == "discernibility_metric":
                assert m.value == pytest.approx(0.0)
            else:
                assert m.value is None

        assert len(report.per_record_risk) == 0
        exps = explain_risk(report)
        assert len(exps) == len(report.metrics)

    def test_json_round_trip(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        eq = build_equivalence_classes(df, qi_columns=["age", "city"])
        report = calculate_class_risk(eq)
        json_str = report.to_json()
        assert isinstance(json_str, str)
        reconstructed = RiskReport.from_json(json_str)
        assert len(reconstructed.metrics) == len(report.metrics)
        for orig, recon in zip(report.metrics, reconstructed.metrics):
            assert orig.name == recon.name
            if orig.value is not None:
                assert orig.value == pytest.approx(recon.value)
            else:
                assert recon.value is None
            assert orig.formula == recon.formula
            assert orig.denominator == recon.denominator
