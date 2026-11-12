"""Integration test: Multi-step mitigation & closed-loop re-evaluation.

Chains age generalization and small class suppression on tiny_people_a.csv,
re-profiles the transformed data, and verifies before/after risk numbers.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from shadowlink.mitigation.models import TransformationSpec
from shadowlink.mitigation.pipeline import run_mitigation_experiment

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")


def test_mitigation_reanalysis_chain() -> None:
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

    report = run_mitigation_experiment(
        original=df,
        specs=specs,
        qi_columns=["age", "city"],
    )

    # Before mitigation
    assert report.before["record_count"] == 8
    assert report.before["k"] == 1
    assert report.before["uniqueness"] == pytest.approx(0.25)
    assert report.before["max_class_risk"] == pytest.approx(1.0)
    assert report.before["average_class_risk"] == pytest.approx(0.625)
    assert report.before["discernibility_metric"] == 14

    # After mitigation
    assert report.after["record_count"] == 7
    assert report.after["k"] == 3
    assert report.after["uniqueness"] == pytest.approx(0.0)
    assert report.after["max_class_risk"] == pytest.approx(1 / 3)
    assert report.after["average_class_risk"] == pytest.approx(2 / 7)
    assert report.after["discernibility_metric"] == 25

    # Suppression fraction: 1 / 8
    assert report.suppression_fraction == pytest.approx(0.125)
    assert len(report.transformation_logs) == 2
