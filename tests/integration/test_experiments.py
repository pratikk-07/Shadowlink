"""Integration tests for benchmark experiments (Tables 5, 6, 7)."""

from __future__ import annotations

import pytest

from shadowlink.evaluator.experiments import (
    run_table5_experiment,
    run_table6_experiment,
    run_table7_experiment,
)


def test_table5_experiment_smoke_and_determinism() -> None:
    df1, md1, csv1 = run_table5_experiment(n=30, seed=123, targets_count=10)
    assert len(df1) == 4
    assert "Step" in df1.columns
    assert "Mean Candidate Risk" in df1.columns
    assert "Table 5" in md1
    assert "# Seed: 123" in csv1

    # Determinism check
    df2, md2, csv2 = run_table5_experiment(n=30, seed=123, targets_count=10)
    assert df1.equals(df2)
    # Strip timestamp comment line for deterministic string comparison
    csv1_body = "\n".join(
        line for line in csv1.splitlines() if not line.startswith("# Generated:")
    )
    csv2_body = "\n".join(
        line for line in csv2.splitlines() if not line.startswith("# Generated:")
    )
    assert csv1_body == csv2_body


def test_table6_experiment_smoke_and_determinism() -> None:
    df1, md1, csv1 = run_table6_experiment(n=30, shared_fraction=0.5, seed=123)
    assert len(df1) == 3
    assert set(df1["Method"]) == {
        "Deterministic (Exact)",
        "Similarity (Jaro-Winkler)",
        "Fellegi-Sunter",
    }
    assert "Precision" in df1.columns
    assert "Recall" in df1.columns
    assert "Table 6" in md1

    # Determinism check
    df2, md2, csv2 = run_table6_experiment(n=30, shared_fraction=0.5, seed=123)
    # Check metric columns are close/equal
    assert df1["Method"].tolist() == df2["Method"].tolist()
    assert df1["True Positives"].tolist() == df2["True Positives"].tolist()
    assert df1["Precision"].tolist() == pytest.approx(df2["Precision"].tolist())


def test_table7_experiment_smoke_and_determinism() -> None:
    df1, md1, csv1 = run_table7_experiment(n=30, shared_fraction=0.5, seed=123)
    assert len(df1) == 5
    assert "Condition" in df1.columns
    assert "Max Class Risk" in df1.columns
    assert "Linkage F1" in df1.columns
    assert "Table 7" in md1

    # Baseline vs combined risk should decrease or remain bounded
    base_mask = df1["Condition"].str.contains("Baseline")
    comb_mask = df1["Condition"].str.contains("Combined")
    base_mean_risk = df1.loc[base_mask, "Mean Class Risk"].iloc[0]
    comb_mean_risk = df1.loc[comb_mask, "Mean Class Risk"].iloc[0]
    assert comb_mean_risk <= base_mean_risk + 1e-6
