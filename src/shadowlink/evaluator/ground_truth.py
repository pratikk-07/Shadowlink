"""Ground truth loading and entity correspondence pairing."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shadowlink.common.exceptions import DatasetLoadError, ValidationError


def load_ground_truth(path: str | Path) -> pd.DataFrame:
    """Load and validate ground truth entity correspondence mapping.

    Ground truth CSV must contain columns: 'dataset', 'record_id', 'entity_id'.
    """
    p = Path(path)
    if not p.exists():
        raise DatasetLoadError(f"Ground truth file '{p}' does not exist.")

    df = pd.read_csv(p)
    required = {"dataset", "record_id", "entity_id"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValidationError(
            f"Ground truth file missing required column(s): {sorted(missing)}."
        )

    return df


def build_true_pairs(
    gt: pd.DataFrame,
    left_dataset: str,
    right_dataset: str,
) -> set[tuple[str, str]]:
    """Construct matching (left_record_id, right_record_id) pairs from ground truth."""
    left_subset = gt[gt["dataset"] == left_dataset][["record_id", "entity_id"]]
    right_subset = gt[gt["dataset"] == right_dataset][["record_id", "entity_id"]]

    merged = pd.merge(left_subset, right_subset, on="entity_id", suffixes=("_l", "_r"))
    true_pairs: set[tuple[str, str]] = set()
    for _, row in merged.iterrows():
        true_pairs.add((str(row["record_id_l"]), str(row["record_id_r"])))

    return true_pairs
