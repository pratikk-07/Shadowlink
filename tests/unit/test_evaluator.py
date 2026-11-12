"""Unit tests for Phase 5 Evaluator, hand calculation oracles, and boundary safety."""

from __future__ import annotations

import ast
import inspect
import pkgutil
from pathlib import Path

import pandas as pd
import pytest

import shadowlink.attacker
import shadowlink.linkage
from shadowlink.common.exceptions import DatasetLoadError, ValidationError
from shadowlink.evaluator.calibration import estimate_m_u_from_ground_truth
from shadowlink.evaluator.ground_truth import build_true_pairs, load_ground_truth
from shadowlink.evaluator.metrics import (
    evaluate_blocking,
    evaluate_linkage_predictions,
    reidentification_success_rate,
)


class TestEvaluatorHandOracles:
    def test_precision_recall_f1_hand_oracle(self) -> None:
        """Hand oracle from specification:

        4 true pairs, 5 predicted matches of which 3 are true
        -> Precision = 3/5 = 0.6
        -> Recall = 3/4 = 0.75
        -> F1 = 2 * (0.6 * 0.75) / (0.6 + 0.75) = 0.9 / 1.35 = 2/3 = 0.6667
        """
        true_pairs = {("L1", "R1"), ("L2", "R2"), ("L3", "R3"), ("L4", "R4")}
        predicted_pairs = pd.DataFrame(
            {
                "left_id": ["L1", "L2", "L3", "L5", "L6"],
                "right_id": ["R1", "R2", "R3", "R5", "R6"],
                "decision": ["match", "match", "match", "match", "match"],
            }
        )

        res = evaluate_linkage_predictions(
            predicted_pairs, true_pairs, total_true_pairs=4
        )
        assert res.true_positives == 3
        assert res.false_positives == 2
        assert res.false_negatives == 1
        assert res.precision == pytest.approx(0.6)
        assert res.recall == pytest.approx(0.75)
        assert res.f1_score == pytest.approx(2 / 3, abs=1e-4)

    def test_reidentification_success_rate_hand_oracle(self) -> None:
        """Hand oracle from specification:

        4 targets:
        - t1: correct unique (credit 1)
        - t2: correct unique (credit 1)
        - t3: true record inside a top tie of size 2 (credit 0.5)
        - t4: true record not a candidate (credit 0)
        -> tie_adjusted = (1 + 1 + 0.5 + 0) / 4 = 2.5 / 4 = 0.625
        -> deterministic = 0.75 when true record has lowest right_id in the tie,
                          0.5 when it has the highest.
        """
        # Ground truth: L1->R1, L2->R2, L3->R3, L4->R4
        truth = pd.DataFrame(
            {
                "dataset": ["A"] * 4 + ["B"] * 4,
                "record_id": ["L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"],
                "entity_id": ["E1", "E2", "E3", "E4", "E1", "E2", "E3", "E4"],
            }
        )

        # Scored pairs:
        # L1: R1 (score 1.0) -> unique top
        # L2: R2 (score 1.0) -> unique top
        # L3: R3 & R9 (both score 1.0) -> tie size 2. Since 'R3' < 'R9', R3 is lowest!
        # L4: R9 (score 1.0) -> true counterpart R4 not a candidate (or score lower)
        scored_pairs_case_a = pd.DataFrame(
            {
                "left_id": ["L1", "L2", "L3", "L3", "L4"],
                "right_id": ["R1", "R2", "R3", "R9", "R9"],
                "score": [1.0, 1.0, 1.0, 1.0, 1.0],
            }
        )

        res_a = reidentification_success_rate(
            scored_pairs_case_a, truth, left_dataset="A", right_dataset="B"
        )
        assert res_a.evaluated_targets_count == 4
        assert res_a.tie_adjusted_success_rate == pytest.approx(0.625)
        # In case a, R3 < R9, so deterministic pick is R3 (correct) -> 3 out of 4 = 0.75
        assert res_a.deterministic_success_rate == pytest.approx(0.75)

        # Case b: R0 & R3 tie for L3, so R0 is picked (incorrect) -> deterministic 0.5
        scored_pairs_case_b = pd.DataFrame(
            {
                "left_id": ["L1", "L2", "L3", "L3", "L4"],
                "right_id": ["R1", "R2", "R0", "R3", "R9"],
                "score": [1.0, 1.0, 1.0, 1.0, 1.0],
            }
        )
        res_b = reidentification_success_rate(
            scored_pairs_case_b, truth, left_dataset="A", right_dataset="B"
        )
        assert res_b.tie_adjusted_success_rate == pytest.approx(0.625)
        assert res_b.deterministic_success_rate == pytest.approx(0.50)

    def test_blocking_evaluation(self) -> None:
        cand_pairs = pd.DataFrame({"left_id": ["L1", "L2"], "right_id": ["R1", "R2"]})
        all_true = {("L1", "R1"), ("L2", "R2"), ("L3", "R3")}
        res = evaluate_blocking(cand_pairs, all_true, naive_comparisons=10)
        assert res.reduction_ratio == pytest.approx(0.8)
        assert res.pairs_completeness == pytest.approx(2 / 3)

    def test_load_ground_truth_and_build_pairs(self, tmp_path: Path) -> None:
        gt_file = tmp_path / "ground_truth.csv"
        df = pd.DataFrame(
            {
                "dataset": ["A", "B"],
                "record_id": ["recA", "recB"],
                "entity_id": ["ent1", "ent1"],
            }
        )
        df.to_csv(gt_file, index=False)

        loaded = load_ground_truth(gt_file)
        assert len(loaded) == 2
        pairs = build_true_pairs(loaded, "A", "B")
        assert pairs == {("recA", "recB")}

        # Test non-existent file
        with pytest.raises(DatasetLoadError):
            load_ground_truth(tmp_path / "missing.csv")

        # Test missing column
        bad_file = tmp_path / "bad.csv"
        pd.DataFrame({"dataset": ["A"], "record_id": ["r1"]}).to_csv(
            bad_file, index=False
        )
        with pytest.raises(ValidationError):
            load_ground_truth(bad_file)

    def test_estimate_m_u_calibration(self) -> None:
        left_df = pd.DataFrame(
            {
                "record_id": ["L1", "L2"],
                "city": ["London", "Paris"],
                "age": [20, 25],
            }
        )
        right_df = pd.DataFrame(
            {
                "record_id": ["R1", "R2"],
                "city": ["London", "Berlin"],
                "age": [20, 25],
            }
        )
        truth = pd.DataFrame(
            {
                "dataset": ["A", "A", "B", "B"],
                "record_id": ["L1", "L2", "R1", "R2"],
                "entity_id": ["E1", "E2", "E1", "E2"],
            }
        )
        candidates = pd.DataFrame(
            {
                "left_id": ["L1", "L1", "L2", "L2"],
                "right_id": ["R1", "R2", "R1", "R2"],
            }
        )

        params = estimate_m_u_from_ground_truth(
            left_df=left_df,
            right_df=right_df,
            candidate_pairs=candidates,
            truth=truth,
            left_dataset="A",
            right_dataset="B",
            attributes=["city", "age"],
            smoothing=1.0,
        )

        assert params.m_probabilities["city"] == pytest.approx(0.5)
        assert params.u_probabilities["city"] == pytest.approx(0.25)
        assert params.m_probabilities["age"] == pytest.approx(0.75)
        assert params.u_probabilities["age"] == pytest.approx(0.25)


class TestGroundTruthBoundaryEnforcement:
    """Non-Negotiable Rule R2:

    (a) linkage/ and attacker/ must never accept, import, read, or mention ground truth.
    (b) Inspect public function signatures for forbidden parameter names.
    (c) AST-scan source for forbidden imports and forbidden literal strings.
    """

    FORBIDDEN_TERMS = {"ground_truth", "truth", "entity_id", "true_id", "identity_key"}

    def test_no_forbidden_parameters_in_linkage_or_attacker(self) -> None:
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
                        for f_term in self.FORBIDDEN_TERMS:
                            assert f_term not in p_lower, (
                                f"Forbidden param '{p}' in function {modname}.{fname}"
                            )

    def test_ast_scan_no_evaluator_imports_or_forbidden_strings(self) -> None:
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
                            assert "evaluator" not in alias.name, (
                                f"Forbidden import of evaluator in {py_file}"
                            )
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        assert "evaluator" not in mod, (
                            f"Forbidden import from evaluator in {py_file}"
                        )
                    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                        val = node.value.lower()
                        # Allow docstrings mentioning the rule, but ban literal column
                        if val in {"ground_truth", "entity_id"}:
                            assert False, (
                                f"Forbidden string constant '{node.value}' in {py_file}"
                            )
