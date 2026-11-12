"""Tests for Attacker Simulator (Phase 2)."""

from __future__ import annotations

import os

import pandas as pd
import pytest

from shadowlink.attacker.models import (
    AttackerProfile,
    KnowledgeSpec,
)
from shadowlink.attacker.simulator import simulate_attack
from shadowlink.common.exceptions import ValidationError
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.metrics import calculate_class_risk

FIXTURE_A_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "tiny_people_a.csv")
)


class TestAttackerSimulatorGoldenFixtureA:
    """Hand-verified oracle tests matching specification on tiny_people_a.csv."""

    def test_golden_two_step_attack_metrics(self) -> None:
        """Hand calculations on tiny_people_a.csv (8 records, all 8 targets):

        Step 1: known (age, city)
          |C| per record = [2, 2, 1, 2, 2, 2, 2, 1]
          mean |C| = 14 / 8 = 1.75
          mean risk = 5 / 8 = 0.625
          unique_fraction = 2 / 8 = 0.25

        Step 2: adds course
          |C| per record = [1, 1, 1, 1, 1, 2, 2, 1]
          mean |C| = 10 / 8 = 1.25
          mean risk = 7 / 8 = 0.875
          unique_fraction = 6 / 8 = 0.75
        """
        df = pd.read_csv(FIXTURE_A_PATH)
        profile = AttackerProfile(
            name="golden_profile",
            steps=[("age", "city"), ("course",)],
        )

        result = simulate_attack(df, profile, n_targets=8, seed=42)

        # Step 1
        s1 = result.step_reports[0]
        assert s1.step == 1
        assert s1.attributes == ["age", "city"]
        assert s1.mean_candidates == pytest.approx(1.75)
        assert s1.mean_risk == pytest.approx(5 / 8)
        assert s1.unique_fraction == pytest.approx(0.25)
        assert s1.expected_success_rate == pytest.approx(s1.mean_risk)

        # Step 2
        s2 = result.step_reports[1]
        assert s2.step == 2
        assert s2.attributes == ["course"]
        assert s2.mean_candidates == pytest.approx(1.25)
        assert s2.mean_risk == pytest.approx(7 / 8)
        assert s2.unique_fraction == pytest.approx(0.75)
        assert s2.expected_success_rate == pytest.approx(s2.mean_risk)

    def test_consistency_with_class_risk_engine(self) -> None:
        """Consistency Requirement:

        Attacker mean_risk and unique_fraction must exactly match
        average_class_risk and singleton_record_proportion from qi_analyser/risk.
        """
        df = pd.read_csv(FIXTURE_A_PATH)

        # Check QI (age, city)
        eq1 = build_equivalence_classes(df, ["age", "city"])
        risk1 = calculate_class_risk(eq1)
        avg_risk1 = next(
            m.value for m in risk1.metrics if m.name == "average_class_risk"
        )
        uniq1 = next(m.value for m in risk1.metrics if m.name == "uniqueness")

        prof1 = AttackerProfile(name="p1", steps=[("age", "city")])
        res1 = simulate_attack(df, prof1, n_targets=len(df), seed=42)
        assert res1.step_reports[0].mean_risk == pytest.approx(avg_risk1)
        assert res1.step_reports[0].unique_fraction == pytest.approx(uniq1)

        # Check QI (age, city, course)
        eq2 = build_equivalence_classes(df, ["age", "city", "course"])
        risk2 = calculate_class_risk(eq2)
        avg_risk2 = next(
            m.value for m in risk2.metrics if m.name == "average_class_risk"
        )
        uniq2 = next(m.value for m in risk2.metrics if m.name == "uniqueness")

        prof2 = AttackerProfile(name="p2", steps=[("age", "city", "course")])
        res2 = simulate_attack(df, prof2, n_targets=len(df), seed=42)
        assert res2.step_reports[0].mean_risk == pytest.approx(avg_risk2)
        assert res2.step_reports[0].unique_fraction == pytest.approx(uniq2)


class TestAttackerSimulatorInvariantsAndEdges:
    def test_monotonic_candidate_reduction(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        profile = AttackerProfile.strong()
        # Ensure df has all required columns
        df_rich = df.copy()
        df_rich["location"] = [
            "North", "North", "South", "South", "East", "East", "East", "West"
        ]
        df_rich["timestamp"] = [f"2026-01-01 10:0{i}:00" for i in range(8)]

        res = simulate_attack(df_rich, profile, n_targets=8, seed=42)
        assert len(res.step_reports) == 4

        prev_mean = len(df_rich)
        for s in res.step_reports:
            assert s.mean_candidates <= prev_mean
            prev_mean = s.mean_candidates

    def test_missing_target_value_skipped(self) -> None:
        df = pd.DataFrame(
            {
                "age": [20, 20, 25, 30],
                "city": ["Delhi", None, "Delhi", "Mumbai"],
            }
        )
        profile = AttackerProfile(name="p", steps=[("age",), ("city",)])
        res = simulate_attack(df, profile, n_targets=4, seed=42)
        # Target index 1 has missing city -> skipped
        assert res.step_reports[1].skipped_attributes_count >= 1

    def test_numeric_tolerance_knowledge(self) -> None:
        df = pd.DataFrame(
            {
                "age": [20, 21, 22, 25],
                "city": ["Kolkata", "Kolkata", "Kolkata", "Kolkata"],
            }
        )
        # Exact age on target 20 -> candidate count = 1
        prof = AttackerProfile(name="p", steps=[("age",)])
        res_exact = simulate_attack(df, prof, n_targets=1, seed=42)
        assert res_exact.step_reports[0].mean_candidates == 1.0

        # Tolerance age +/- 1 on target 20 -> candidates 20, 21 -> count = 2
        res_tol = simulate_attack(
            df,
            prof,
            n_targets=1,
            seed=42,
            knowledge={"age": KnowledgeSpec(kind="numeric_tolerance", tolerance=1.0)},
        )
        assert res_tol.step_reports[0].mean_candidates == 2.0

    def test_invalid_attribute_rejected(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        prof = AttackerProfile(name="bad", steps=[("nonexistent_column",)])
        with pytest.raises(ValidationError, match="not found"):
            simulate_attack(df, prof, n_targets=5, seed=42)

    def test_tidy_dataframe_export(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        prof = AttackerProfile.moderate()
        res = simulate_attack(df, prof, n_targets=4, seed=42)
        df_out = res.to_dataframe()
        assert isinstance(df_out, pd.DataFrame)
        assert len(df_out) == 2
        assert "mean_candidates" in df_out.columns
        assert "mean_risk" in df_out.columns
