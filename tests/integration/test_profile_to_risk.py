"""Integration test: End-to-end pipeline from data profiling to risk calculation.

Verifies that loading a CSV file, profiling it, extracting candidate QIs,
constructing equivalence classes, and evaluating risk produces exact hand-calculated
oracle metrics on tiny_people_a.csv.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadowlink.profiler.profiler import profile_csv
from shadowlink.qi_analyser.candidates import find_candidate_qis
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.explanations import explain_risk
from shadowlink.risk.metrics import calculate_class_risk

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")


def test_end_to_end_profile_to_risk() -> None:
    # 1. Profile the dataset
    profile = profile_csv(FIXTURE_A_PATH, dataset_name="fixture_a")
    assert profile.row_count == 8
    assert profile.column_count == 3
    assert profile.duplicate_row_count == 1

    # 2. Candidate QI detection
    candidates = find_candidate_qis([profile])
    candidate_names = [c.column_name for c in candidates]
    # Age has uniqueness ratio 0.50 >= 0.50 -> candidate
    assert "age" in candidate_names

    # 3. Form equivalence classes over chosen QIs [age, city]
    import pandas as pd

    df = pd.read_csv(FIXTURE_A_PATH)
    eq = build_equivalence_classes(df, qi_columns=["age", "city"])
    assert eq.k == 1
    assert eq.num_classes == 5
    assert eq.singleton_record_count == 2
    assert eq.singleton_record_proportion == pytest.approx(0.25)

    # 4. Compute risk metrics
    risk_report = calculate_class_risk(eq)
    metric_map = {m.name: m for m in risk_report.metrics}

    assert metric_map["k_anonymity"].value == pytest.approx(1.0)
    assert metric_map["max_class_risk"].value == pytest.approx(1.0)
    assert metric_map["average_class_risk"].value == pytest.approx(0.625)
    assert metric_map["uniqueness"].value == pytest.approx(0.25)
    assert metric_map["discernibility_metric"].value == pytest.approx(14.0)

    # 5. Generate human-readable explanations
    explanations = explain_risk(risk_report)
    assert len(explanations) == len(risk_report.metrics)
    assert any(e.level == "CRITICAL" for e in explanations)

