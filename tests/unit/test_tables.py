"""Unit tests for table formatting and experiment metadata."""

from __future__ import annotations

import pandas as pd

from shadowlink.evaluator.tables import (
    format_csv_with_header,
    format_markdown_table,
    generate_experiment_metadata,
)


def test_table_formatting() -> None:
    df = pd.DataFrame(
        {
            "Method": ["Deterministic", "Fellegi-Sunter"],
            "Score": [0.85231, 0.99128],
            "Count": [10, 20],
        }
    )

    md = format_markdown_table(df, title="Benchmark Results")
    assert "### Benchmark Results" in md
    assert "| Method" in md
    assert "0.8523" in md

    meta = generate_experiment_metadata(
        "Unit Test Experiment", n=50, seed=42, shared_fraction=0.4
    )
    assert "# Experiment: Unit Test Experiment" in meta
    assert "# Population N: 50" in meta
    assert "# Seed: 42" in meta
    assert "# Shared Fraction: 0.4" in meta

    csv_out = format_csv_with_header(df, meta)
    assert csv_out.startswith("# Experiment:")
    assert "Method,Score,Count" in csv_out

