"""Unit tests for mitigation evaluation and linkage tradeoffs."""

from __future__ import annotations

import pandas as pd
import pytest

from shadowlink.evaluator.mitigation_eval import (
    evaluate_mitigation_linkage_tradeoff,
    evaluate_mitigation_on_dataset,
)


def test_evaluate_mitigation_on_dataset() -> None:
    orig = pd.DataFrame(
        {
            "record_id": ["1", "2", "3", "4"],
            "age": [20, 20, 25, 25],
            "city": ["London", "London", "Paris", "Paris"],
        }
    )
    # Mitigate age by generalizing all to '20-29'
    mit = pd.DataFrame(
        {
            "record_id": ["1", "2", "3", "4"],
            "age": ["20-29", "20-29", "20-29", "20-29"],
            "city": ["London", "London", "Paris", "Paris"],
        }
    )

    stats = evaluate_mitigation_on_dataset(orig, mit, qi_columns=["age", "city"])
    assert "baseline_max_risk" in stats
    assert "mitigated_max_risk" in stats
    assert stats["utility_loss"] == pytest.approx(0.5)  # half the non-id cells changed


def test_evaluate_mitigation_linkage_tradeoff() -> None:
    left = pd.DataFrame(
        {"record_id": ["L1", "L2"], "city": ["London", "Paris"], "age": [20, 30]}
    )
    right = pd.DataFrame(
        {"record_id": ["R1", "R2"], "city": ["London", "Paris"], "age": [20, 30]}
    )
    # Fully suppress city to SUPPRESSED
    left_mit = pd.DataFrame(
        {
            "record_id": ["L1", "L2"],
            "city": ["SUPPRESSED", "SUPPRESSED"],
            "age": [20, 30],
        }
    )
    right_mit = pd.DataFrame(
        {
            "record_id": ["R1", "R2"],
            "city": ["SUPPRESSED", "SUPPRESSED"],
            "age": [20, 30],
        }
    )
    truth = pd.DataFrame(
        {
            "dataset": ["A", "A", "B", "B"],
            "record_id": ["L1", "L2", "R1", "R2"],
            "entity_id": ["E1", "E2", "E1", "E2"],
        }
    )

    rep = evaluate_mitigation_linkage_tradeoff(
        orig_left=left,
        orig_right=right,
        mit_left=left_mit,
        mit_right=right_mit,
        truth=truth,
        left_dataset="A",
        right_dataset="B",
        qi_columns=["city", "age"],
        blocking_keys=["city"],
        mitigation_name="suppress_city",
    )
    assert rep.mitigation_name == "suppress_city"
    assert rep.baseline_linkage_f1 >= 0.0
    assert rep.utility_loss == pytest.approx(0.5)

