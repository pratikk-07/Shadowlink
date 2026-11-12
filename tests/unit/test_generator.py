"""Tests for Synthetic Data Generator (Phase 1)."""

from __future__ import annotations

import tempfile

import numpy as np
import pytest

from shadowlink.common.exceptions import ConfigError, ValidationError
from shadowlink.generator.generator import (
    generate_synthetic_bundle,
    report_abc,
    wide_release,
)
from shadowlink.generator.io import load_bundle, write_bundle
from shadowlink.generator.models import (
    DatasetSpec,
    GeneratorConfig,
)
from shadowlink.generator.noise import inject_typo


class TestGeneratorConfigValidation:
    def test_invalid_population_size(self) -> None:
        with pytest.raises(ValidationError, match="population_size"):
            GeneratorConfig(
                seed=42,
                population_size=0,
                shared_fraction=0.5,
                datasets=[DatasetSpec(name="A", attributes=["age"])],
            )

    def test_invalid_shared_fraction(self) -> None:
        with pytest.raises(ValidationError, match="shared_fraction"):
            GeneratorConfig(
                seed=42,
                population_size=10,
                shared_fraction=1.5,
                datasets=[DatasetSpec(name="A", attributes=["age"])],
            )

    def test_empty_datasets_list(self) -> None:
        with pytest.raises(ConfigError, match="datasets list"):
            GeneratorConfig(
                seed=42,
                population_size=10,
                shared_fraction=0.5,
                datasets=[],
            )

    def test_duplicate_dataset_names(self) -> None:
        with pytest.raises(ConfigError, match="unique"):
            GeneratorConfig(
                seed=42,
                population_size=10,
                shared_fraction=0.5,
                datasets=[
                    DatasetSpec(name="A", attributes=["age"]),
                    DatasetSpec(name="A", attributes=["city"]),
                ],
            )

    def test_forbidden_column_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            DatasetSpec(name="A", attributes=["age", "true_id"])

    def test_record_id_in_spec_rejected(self) -> None:
        with pytest.raises(ValidationError, match="reserved"):
            DatasetSpec(name="A", attributes=["age", "record_id"])


class TestTypoGenerator:
    def test_typo_always_differs_and_non_empty(self) -> None:
        rng = np.random.default_rng(1234)
        words = ["Kolkata", "Delhi", "CSE", "Ganga", "A", "Hi"]
        for word in words:
            for _ in range(50):
                typo = inject_typo(word, rng)
                assert typo != word
                assert len(typo) > 0


class TestSyntheticDataGeneration:
    def test_exact_hand_computed_counts(self) -> None:
        """Hand calculation: N=10, f=0.4 -> 4 shared entities.

        Remaining 6 entities split equally across 2 datasets (3 each).
        Each dataset has size: 4 shared + 3 exclusive = 7 records.
        Total records across datasets = 14.
        """
        config = GeneratorConfig(
            seed=42,
            population_size=10,
            shared_fraction=0.4,
            datasets=[
                DatasetSpec(name="A", attributes=["age", "city"]),
                DatasetSpec(name="B", attributes=["city", "course"]),
            ],
        )
        bundle = generate_synthetic_bundle(config)

        assert len(bundle.datasets["A"]) == 7
        assert len(bundle.datasets["B"]) == 7
        assert len(bundle.ground_truth) == 14
        assert bundle.manifest["shared_count"] == 4

    def test_every_person_in_at_least_one_dataset(self) -> None:
        config = GeneratorConfig(
            seed=101,
            population_size=30,
            shared_fraction=0.2,
            datasets=[
                DatasetSpec(name="A", attributes=["age"]),
                DatasetSpec(name="B", attributes=["city"]),
                DatasetSpec(name="C", attributes=["course"]),
            ],
        )
        bundle = generate_synthetic_bundle(config)
        gt = bundle.ground_truth
        unique_entities = set(gt["entity_id"].unique())
        assert len(unique_entities) == 30

    def test_shared_people_appear_in_all_datasets(self) -> None:
        config = GeneratorConfig(
            seed=202,
            population_size=20,
            shared_fraction=0.5,
            datasets=[
                DatasetSpec(name="D1", attributes=["age"]),
                DatasetSpec(name="D2", attributes=["city"]),
            ],
        )
        bundle = generate_synthetic_bundle(config)
        gt = bundle.ground_truth
        d1_entities = set(gt[gt["dataset"] == "D1"]["entity_id"])
        d2_entities = set(gt[gt["dataset"] == "D2"]["entity_id"])
        shared = d1_entities.intersection(d2_entities)
        assert len(shared) == 10  # round(0.5 * 20)

    def test_zero_noise_ground_truth_consistency(self) -> None:
        """With noise=0, records matching the same entity_id share identical values."""
        config = GeneratorConfig(
            seed=303,
            population_size=15,
            shared_fraction=1.0,
            datasets=[
                DatasetSpec(
                    name="A",
                    attributes=["age", "city"],
                    typo_rate=0.0,
                    missing_rate=0.0,
                ),
                DatasetSpec(
                    name="B",
                    attributes=["age", "city"],
                    typo_rate=0.0,
                    missing_rate=0.0,
                ),
            ],
        )
        bundle = generate_synthetic_bundle(config)
        df_a = bundle.datasets["A"]
        df_b = bundle.datasets["B"]
        gt = bundle.ground_truth

        for entity_id in gt["entity_id"].unique():
            sub_a = gt[(gt["entity_id"] == entity_id) & (gt["dataset"] == "A")]
            sub_b = gt[(gt["entity_id"] == entity_id) & (gt["dataset"] == "B")]
            r_a = sub_a["record_id"].iloc[0]
            r_b = sub_b["record_id"].iloc[0]

            val_a = df_a[df_a["record_id"] == r_a][["age", "city"]].iloc[0].to_dict()
            val_b = df_b[df_b["record_id"] == r_b][["age", "city"]].iloc[0].to_dict()
            assert val_a == val_b

    def test_determinism_same_seed_identical(self) -> None:
        cfg1 = GeneratorConfig(
            seed=999,
            population_size=10,
            shared_fraction=0.5,
            datasets=[DatasetSpec(name="A", attributes=["city"], typo_rate=0.2)],
        )
        cfg2 = GeneratorConfig(
            seed=999,
            population_size=10,
            shared_fraction=0.5,
            datasets=[DatasetSpec(name="A", attributes=["city"], typo_rate=0.2)],
        )
        b1 = generate_synthetic_bundle(cfg1)
        b2 = generate_synthetic_bundle(cfg2)
        assert b1.datasets["A"].equals(b2.datasets["A"])
        assert b1.ground_truth.equals(b2.ground_truth)

    def test_different_seed_different_data(self) -> None:
        cfg1 = GeneratorConfig(
            seed=1,
            population_size=10,
            shared_fraction=0.5,
            datasets=[DatasetSpec(name="A", attributes=["city"])],
        )
        cfg2 = GeneratorConfig(
            seed=2,
            population_size=10,
            shared_fraction=0.5,
            datasets=[DatasetSpec(name="A", attributes=["city"])],
        )
        b1 = generate_synthetic_bundle(cfg1)
        b2 = generate_synthetic_bundle(cfg2)
        assert not b1.datasets["A"].equals(b2.datasets["A"])

    def test_presets_execution(self) -> None:
        bundle_abc = report_abc(seed=42, population_size=50, shared_fraction=0.4)
        assert set(bundle_abc.datasets.keys()) == {"A", "B", "C"}
        assert "record_id" in bundle_abc.datasets["A"].columns
        assert "entity_id" not in bundle_abc.datasets["A"].columns

        bundle_wide = wide_release(seed=42, population_size=50)
        assert set(bundle_wide.datasets.keys()) == {"W"}
        assert len(bundle_wide.datasets["W"]) == 50

    def test_io_bundle_round_trip(self) -> None:
        bundle = report_abc(seed=77, population_size=20, shared_fraction=0.5)
        with tempfile.TemporaryDirectory() as td:
            write_bundle(bundle, td)
            loaded = load_bundle(td)
            assert set(loaded.datasets.keys()) == set(bundle.datasets.keys())
            assert len(loaded.ground_truth) == len(bundle.ground_truth)
            assert loaded.manifest["seed"] == 77
