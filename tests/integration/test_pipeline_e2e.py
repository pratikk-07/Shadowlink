"""Integration tests for the complete 9-stage end-to-end pipeline."""

from __future__ import annotations

import ast
import inspect
import pkgutil
from pathlib import Path

import pandas as pd
import pytest

import shadowlink.attacker
import shadowlink.linkage
from shadowlink.attacker.models import AttackerProfile
from shadowlink.attacker.simulator import simulate_attack
from shadowlink.cli.main import main
from shadowlink.common.exceptions import ValidationError
from shadowlink.mitigation.models import TransformationSpec
from shadowlink.pipeline.models import PipelineConfig
from shadowlink.pipeline.runner import PipelineStageError, run_pipeline
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.metrics import calculate_class_risk

FIXTURE_A_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "tiny_people_a.csv"
)


class TestPipelineEndToEnd:
    """Verifies all requirements for the 9-stage pipeline."""

    def test_pipeline_runs_all_stages_and_is_deterministic(
        self, tmp_path: Path
    ) -> None:
        """Run all stages with small N and verify deterministic identical outputs."""
        config = PipelineConfig(
            seed=42,
            generator_preset="report_abc",
            population_size=30,
            shared_fraction=0.5,
            typo_rate=0.0,
            missing_rate=0.0,
            target_dataset="A",
            qi_columns=["age", "city"],
            attacker_steps=[("age", "city"), ("course",)],
            attacker_targets=15,
            linkage_left="A",
            linkage_right="B",
            linkage_blocking_keys=["city"],
            linkage_attributes=["age", "city"],
            linkage_threshold=0.85,
            mitigation_transformations=[
                TransformationSpec(
                    kind="generalize_age",
                    parameters={"column": "age", "bin_width": 5},
                )
            ],
        )

        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"

        rep1 = run_pipeline(config, out_dir=out1)
        _ = run_pipeline(config, out_dir=out2)

        # Verify all 9 stages are populated
        d1 = rep1.to_dict()
        assert "metadata" in d1
        assert "stage1_generation" in d1
        assert "stage2_profiles" in d1
        assert "stage3_shared_and_qis" in d1
        assert "stage4_risk" in d1
        assert "stage5_attacker" in d1
        assert "stage6_linkage" in d1
        assert "stage7_mitigation" in d1
        assert "stage8_evaluation" in d1

        # Check (c): re-running gives identical output
        json1 = (out1 / "report.json").read_text(encoding="utf-8")
        json2 = (out2 / "report.json").read_text(encoding="utf-8")
        assert json1 == json2

        md1 = (out1 / "report.md").read_text(encoding="utf-8")
        md2 = (out2 / "report.md").read_text(encoding="utf-8")
        assert md1 == md2

    def test_attacker_curve_equals_class_based_risk_on_8_row_fixture(
        self,
    ) -> None:
        """Requirement (a):

        Attacker curve equals class-based risk on tiny_people_a.csv (8 records).
        """
        df = pd.read_csv(FIXTURE_A_PATH)
        assert len(df) == 8

        # Step 1: (age, city)
        eq1 = build_equivalence_classes(df, ["age", "city"])
        risk1 = calculate_class_risk(eq1)
        r_map1 = {m.name: m.value for m in risk1.metrics}
        avg_risk1 = r_map1["average_class_risk"]
        uniq1 = r_map1["uniqueness"]

        prof = AttackerProfile(
            name="p_fixture", steps=[("age", "city"), ("course",)]
        )
        res = simulate_attack(df, prof, n_targets=len(df), seed=42)

        step1 = res.step_reports[0]
        assert step1.mean_risk == pytest.approx(avg_risk1)
        assert step1.unique_fraction == pytest.approx(uniq1)
        assert step1.mean_risk == pytest.approx(5 / 8)
        assert step1.unique_fraction == pytest.approx(0.25)

        # Step 2: (age, city) + (course,)
        eq2 = build_equivalence_classes(df, ["age", "city", "course"])
        risk2 = calculate_class_risk(eq2)
        r_map2 = {m.name: m.value for m in risk2.metrics}
        avg_risk2 = r_map2["average_class_risk"]
        uniq2 = r_map2["uniqueness"]

        step2 = res.step_reports[1]
        assert step2.mean_risk == pytest.approx(avg_risk2)
        assert step2.unique_fraction == pytest.approx(uniq2)
        assert step2.mean_risk == pytest.approx(7 / 8)
        assert step2.unique_fraction == pytest.approx(0.75)

    def test_ground_truth_boundary_rules_still_pass(self) -> None:
        """Requirement (b):

        Inspect linkage and attacker modules to ensure rule R2 still holds:
        (1) No forbidden parameter names.
        (2) No evaluator imports or forbidden string constants.
        """
        forbidden = {
            "ground_truth",
            "truth",
            "entity_id",
            "true_id",
            "identity_key",
        }
        for pkg in [shadowlink.linkage, shadowlink.attacker]:
            for _, modname, _ in pkgutil.walk_packages(
                pkg.__path__, prefix=f"{pkg.__name__}."
            ):
                mod = __import__(modname, fromlist=["_"])
                for fname, func in inspect.getmembers(mod, inspect.isfunction):
                    if fname.startswith("_"):
                        continue
                    sig = inspect.signature(func)
                    for p in sig.parameters:
                        p_lower = p.lower()
                        for f_term in forbidden:
                            assert f_term not in p_lower, (
                                f"Forbidden param '{p}' in function {modname}.{fname}"
                            )

        src_root = Path(shadowlink.__file__).resolve().parent
        for target_pkg in ["linkage", "attacker"]:
            pkg_dir = src_root / target_pkg
            for py_file in pkg_dir.rglob("*.py"):
                tree = ast.parse(
                    py_file.read_text(encoding="utf-8"), filename=str(py_file)
                )
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert "evaluator" not in alias.name
                    elif isinstance(node, ast.ImportFrom):
                        mod_name = node.module or ""
                        assert "evaluator" not in mod_name
                    elif isinstance(node, ast.Constant) and isinstance(
                        node.value, str
                    ):
                        val = node.value.lower()
                        if val in {"ground_truth", "entity_id"}:
                            assert False, (
                                f"Forbidden string constant '{node.value}' in {py_file}"
                            )

    def test_pipeline_stage_error_on_invalid_stage(self) -> None:
        """Requirement: Clear error with stage name if any stage fails."""
        bad_config = PipelineConfig(
            target_dataset="NON_EXISTENT_DATASET",
        )
        with pytest.raises(PipelineStageError) as exc_info:
            run_pipeline(bad_config)
        assert "[Stage 4: Equivalence Classes & Class Risk]" in str(
            exc_info.value
        )

    def test_pipeline_config_serialization_and_cli(
        self, tmp_path: Path
    ) -> None:
        cfg = PipelineConfig(
            seed=101,
            generator_preset="report_abc",
            population_size=20,
            shared_fraction=0.5,
            typo_rate=0.0,
            missing_rate=0.0,
            target_dataset="A",
            qi_columns=["age", "city"],
            attacker_steps=[("age", "city")],
            attacker_targets=10,
            linkage_left="A",
            linkage_right="B",
            linkage_blocking_keys=["city"],
            linkage_attributes=["age", "city"],
            linkage_threshold=0.85,
            mitigation_transformations=[
                TransformationSpec(
                    kind="generalize_age",
                    parameters={"column": "age", "bin_width": 5},
                )
            ],
        )
        d = cfg.to_dict()
        cfg_roundtrip = PipelineConfig.from_dict(d)
        assert cfg_roundtrip.seed == 101
        assert cfg_roundtrip.population_size == 20

        cfg_file = tmp_path / "test_pipeline.json"
        import json

        cfg_file.write_text(json.dumps(d), encoding="utf-8")

        loaded = PipelineConfig.from_json(cfg_file)
        assert loaded.seed == 101

        # Test CLI run-pipeline
        cli_out = tmp_path / "cli_run"
        ret = main(
            ["run-pipeline", "--config", str(cfg_file), "--out", str(cli_out)]
        )
        assert ret == 0
        assert (cli_out / "report.json").exists()
        assert (cli_out / "report.md").exists()

        # Test invalid JSON raises ValidationError
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ValidationError):
            PipelineConfig.from_json(bad_json)
