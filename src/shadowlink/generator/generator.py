"""Synthetic Data Generator orchestrator and standard presets."""

from __future__ import annotations

import platform
from typing import Any

import numpy as np
import pandas as pd

from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.generator.attributes import generate_latent_population
from shadowlink.generator.models import (
    DatasetSpec,
    GeneratedBundle,
    GeneratorConfig,
    TimestampWindow,
)
from shadowlink.generator.noise import apply_noise


def _partition_exclusive_counts(
    total_exclusive: int, weights: list[float]
) -> list[int]:
    """Deterministically partition exclusive entities using largest remainder."""
    k = len(weights)
    if k == 0 or total_exclusive == 0:
        return [0] * k

    total_w = sum(weights)
    norm_w = [w / total_w for w in weights]

    exact_counts = [w * total_exclusive for w in norm_w]
    int_counts = [int(np.floor(c)) for c in exact_counts]
    remainder = total_exclusive - sum(int_counts)

    fractions = [exact_counts[i] - int_counts[i] for i in range(k)]
    # Break ties deterministically by index
    sorted_indices = sorted(range(k), key=lambda i: (-fractions[i], i))

    for idx in sorted_indices[:remainder]:
        int_counts[idx] += 1

    return int_counts


def generate_synthetic_bundle(config: GeneratorConfig) -> GeneratedBundle:
    """Generate multi-dataset synthetic bundle with ground truth and manifest."""
    rng = np.random.default_rng(config.seed)
    n = config.population_size

    latent_pop = generate_latent_population(
        n=n,
        rng=rng,
        timestamp_window=config.timestamp_window,
    )

    n_shared = int(round(config.shared_fraction * n))
    permuted_entities = rng.permutation(latent_pop["entity_id"].values)

    shared_entities = set(permuted_entities[:n_shared])
    exclusive_pool = list(permuted_entities[n_shared:])

    weights = config.exclusive_weights or [1.0] * len(config.datasets)
    exclusive_counts = _partition_exclusive_counts(len(exclusive_pool), weights)

    dataset_dfs: dict[str, pd.DataFrame] = {}
    ground_truth_records: list[dict[str, str]] = []
    total_typos = 0
    total_missing = 0
    per_dataset_counts: dict[str, int] = {}

    current_idx = 0
    for d_idx, d_spec in enumerate(config.datasets):
        ex_count = exclusive_counts[d_idx]
        d_exclusive = exclusive_pool[current_idx : current_idx + ex_count]
        current_idx += ex_count

        member_ids = list(shared_entities) + d_exclusive
        per_dataset_counts[d_spec.name] = len(member_ids)

        sub_df = latent_pop[latent_pop["entity_id"].isin(member_ids)].copy()

        # Shuffle rows so record_id order carries zero entity-order information
        shuffle_perm = rng.permutation(len(sub_df))
        shuffled_sub = sub_df.iloc[shuffle_perm].reset_index(drop=True)

        record_ids = [f"{d_spec.name}-{i + 1:05d}" for i in range(len(shuffled_sub))]
        for r_id, e_id in zip(record_ids, shuffled_sub["entity_id"]):
            ground_truth_records.append(
                {
                    "dataset": d_spec.name,
                    "record_id": str(r_id),
                    "entity_id": str(e_id),
                }
            )

        # Projected columns: record_id first, then chosen attributes
        projected = pd.DataFrame({"record_id": record_ids})
        for attr in d_spec.attributes:
            projected[attr] = shuffled_sub[attr].values

        # Apply noise (typos + missing values)
        noisy_proj, typos, missing = apply_noise(
            projected,
            typo_rate=d_spec.typo_rate,
            missing_rate=d_spec.missing_rate,
            rng=rng,
            id_column="record_id",
        )

        validate_no_forbidden_columns(noisy_proj)
        dataset_dfs[d_spec.name] = noisy_proj
        total_typos += typos
        total_missing += missing

    ground_truth_df = pd.DataFrame(ground_truth_records)

    manifest: dict[str, Any] = {
        "config": config.to_dict(),
        "seed": config.seed,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "population_size": n,
        "shared_count": n_shared,
        "per_dataset_record_counts": per_dataset_counts,
        "total_typos_injected": total_typos,
        "total_missing_injected": total_missing,
    }

    return GeneratedBundle(
        datasets=dataset_dfs,
        ground_truth=ground_truth_df,
        manifest=manifest,
    )


def report_abc(
    seed: int = 42,
    population_size: int = 1000,
    shared_fraction: float = 0.3,
    typo_rate: float = 0.05,
    missing_rate: float = 0.02,
) -> GeneratedBundle:
    """Preset matching the project report architecture (Datasets A, B, and C)."""
    datasets = [
        DatasetSpec(
            name="A",
            attributes=["age", "city", "course"],
            typo_rate=typo_rate,
            missing_rate=missing_rate,
        ),
        DatasetSpec(
            name="B",
            attributes=["age", "city", "location", "timestamp"],
            typo_rate=typo_rate,
            missing_rate=missing_rate,
        ),
        DatasetSpec(
            name="C",
            attributes=["course", "hostel", "club"],
            typo_rate=typo_rate,
            missing_rate=missing_rate,
        ),
    ]
    config = GeneratorConfig(
        seed=seed,
        population_size=population_size,
        shared_fraction=shared_fraction,
        datasets=datasets,
        timestamp_window=TimestampWindow(start_date="2026-01-01", days=30),
    )
    return generate_synthetic_bundle(config)


def wide_release(
    seed: int = 42,
    population_size: int = 1000,
) -> GeneratedBundle:
    """Preset with wide demographic & behavioural release (for Attacker experiments)."""
    datasets = [
        DatasetSpec(
            name="W",
            attributes=["age", "city", "course", "location", "timestamp"],
            typo_rate=0.0,
            missing_rate=0.0,
        )
    ]
    config = GeneratorConfig(
        seed=seed,
        population_size=population_size,
        shared_fraction=1.0,
        datasets=datasets,
    )
    return generate_synthetic_bundle(config)
