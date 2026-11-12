"""Persistence helpers for GeneratedBundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from shadowlink.common.exceptions import DatasetLoadError
from shadowlink.generator.models import GeneratedBundle


def write_bundle(bundle: GeneratedBundle, out_dir: str | Path) -> None:
    """Save datasets, ground truth, and manifest to a target directory."""
    target_path = Path(out_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    # Write each dataset as CSV
    for name, df in bundle.datasets.items():
        csv_file = target_path / f"{name}.csv"
        df.to_csv(csv_file, index=False)

    # Write ground truth CSV
    gt_file = target_path / "ground_truth.csv"
    bundle.ground_truth.to_csv(gt_file, index=False)

    # Write manifest JSON
    manifest_file = target_path / "manifest.json"
    manifest_file.write_text(json.dumps(bundle.manifest, indent=2), encoding="utf-8")


def load_bundle(dir_path: str | Path) -> GeneratedBundle:
    """Load an existing GeneratedBundle from disk."""
    base = Path(dir_path)
    if not base.exists():
        raise DatasetLoadError(f"Directory '{base}' does not exist.")

    manifest_file = base / "manifest.json"
    if not manifest_file.exists():
        raise DatasetLoadError(f"Manifest file '{manifest_file}' missing.")

    manifest: dict[str, Any] = json.loads(manifest_file.read_text(encoding="utf-8"))

    gt_file = base / "ground_truth.csv"
    if not gt_file.exists():
        raise DatasetLoadError(f"Ground truth file '{gt_file}' missing.")
    ground_truth = pd.read_csv(gt_file)

    datasets: dict[str, pd.DataFrame] = {}
    cfg = manifest.get("config", {})
    dataset_specs = cfg.get("datasets", [])
    for d_spec in dataset_specs:
        name = d_spec["name"]
        csv_file = base / f"{name}.csv"
        if not csv_file.exists():
            raise DatasetLoadError(f"Dataset CSV '{csv_file}' missing.")
        datasets[name] = pd.read_csv(csv_file)

    return GeneratedBundle(
        datasets=datasets,
        ground_truth=ground_truth,
        manifest=manifest,
    )

