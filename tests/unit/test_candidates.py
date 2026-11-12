"""Unit tests for Candidate-set risk and QI Analyser candidate selection (Phase 4).

Covers:
- calculate_candidate_risk with [100, 20, 5] and initial 100
- candidate_count == 0 edge case (risk is None, explanation 'no candidate')
- AttackerStepSummary contract consumption
- find_candidate_qis on Fixtures A + B:
    - age: flagged (uniqueness 0.5 >= 0.5 and shared with B)
    - city: flagged (shared with B)
    - course: not flagged (uniqueness 0.25 < 0.5 and not shared)
- Exclusion of all-null and constant columns
- QISelection immutable operations: confirm, reject, add_manual
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.schemas import AttackerStepSummary
from shadowlink.profiler.profiler import profile_csv
from shadowlink.qi_analyser.candidates import (
    QIHeuristics,
    QISelection,
    find_candidate_qis,
)
from shadowlink.risk.metrics import (
    calculate_candidate_risk,
    calculate_candidate_risk_from_steps,
)

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")
FIXTURE_B_PATH = Path("tests/fixtures/tiny_people_b.csv")


class TestCandidateSetRisk:
    """Tests for progressive attacker candidate narrowing risk."""

    def test_calculate_candidate_risk_standard_progression(self) -> None:
        # Initial count = 100
        # Steps: [100, 20, 5]
        # Step 0: count=100 -> risk=1/100=0.01, reduction=1 - 100/100 = 0.0
        # Step 1: count=20  -> risk=1/20=0.05,  reduction=1 - 20/100  = 0.80
        # Step 2: count=5   -> risk=1/5=0.20,   reduction=1 - 5/100   = 0.95
        report = calculate_candidate_risk([100, 20, 5], initial_count=100)

        assert report.initial_count == 100
        assert len(report.steps) == 3

        s0 = report.steps[0]
        assert s0.step == 0
        assert s0.candidate_count == 100
        assert s0.risk == pytest.approx(0.01)
        assert s0.candidate_reduction == pytest.approx(0.0)

        s1 = report.steps[1]
        assert s1.step == 1
        assert s1.candidate_count == 20
        assert s1.risk == pytest.approx(0.05)
        assert s1.candidate_reduction == pytest.approx(0.80)

        s2 = report.steps[2]
        assert s2.step == 2
        assert s2.candidate_count == 5
        assert s2.risk == pytest.approx(0.20)
        assert s2.candidate_reduction == pytest.approx(0.95)

    def test_candidate_risk_zero_count(self) -> None:
        # If candidate set shrinks to 0 (contradictory auxiliary info)
        # risk must be None and explanation must state 'no candidate'
        report = calculate_candidate_risk([10, 0], initial_count=10)
        assert report.steps[1].candidate_count == 0
        assert report.steps[1].risk is None
        assert "no candidate" in report.steps[1].explanation.lower()
        assert report.steps[1].candidate_reduction == pytest.approx(1.0)

    def test_calculate_candidate_risk_from_steps(self) -> None:
        steps = [
            AttackerStepSummary(step=0, known_attributes=["age"], candidate_count=50),
            AttackerStepSummary(
                step=1, known_attributes=["age", "city"], candidate_count=10
            ),
            AttackerStepSummary(
                step=2,
                known_attributes=["age", "city", "location"],
                candidate_count=2,
            ),
        ]
        report = calculate_candidate_risk_from_steps(steps, initial_count=100)
        assert len(report.steps) == 3
        assert report.steps[0].risk == pytest.approx(1 / 50)
        assert report.steps[1].risk == pytest.approx(1 / 10)
        assert report.steps[2].risk == pytest.approx(1 / 2)

    def test_candidate_risk_validation_errors(self) -> None:
        with pytest.raises(ValidationError, match="initial_count must be > 0"):
            calculate_candidate_risk([10], initial_count=0)

        with pytest.raises(ValidationError, match="cannot exceed initial_count"):
            calculate_candidate_risk([105], initial_count=100)

        with pytest.raises(ValidationError, match="cannot be negative"):
            calculate_candidate_risk([-1], initial_count=100)


class TestCandidateQIHeuristics:
    """Evaluation of QI heuristics on fixtures A and B."""

    def test_fixture_a_and_b_candidates(self) -> None:
        prof_a = profile_csv(FIXTURE_A_PATH, dataset_name="A")
        prof_b = profile_csv(FIXTURE_B_PATH, dataset_name="B")

        candidates = find_candidate_qis([prof_a, prof_b], heuristics=QIHeuristics())

        # Check candidates for dataset A
        a_cand_map = {c.column_name: c for c in candidates if c.dataset_name == "A"}

        # Age in A: uniqueness 0.50 >= 0.50, and shared with B -> flagged
        assert "age" in a_cand_map
        age_cand = a_cand_map["age"]
        assert age_cand.status == "suggested"
        assert any("uniqueness" in r.lower() for r in age_cand.reasons)
        assert any("shared" in r.lower() for r in age_cand.reasons)

        # City in A: uniqueness 0.375 < 0.50, but shared with B -> flagged
        assert "city" in a_cand_map
        city_cand = a_cand_map["city"]
        assert city_cand.status == "suggested"
        assert any("shared" in r.lower() for r in city_cand.reasons)

        # Course in A: uniqueness 0.25 < 0.50 and not shared -> NOT flagged
        assert "course" not in a_cand_map

    def test_constant_and_all_null_excluded(self) -> None:
        import pandas as pd

        from shadowlink.profiler.profiler import profile_dataframe

        df = pd.DataFrame(
            {
                "age": [20, 25, 30],
                "const_col": ["X", "X", "X"],
                "null_col": [None, None, None],
            }
        )
        prof = profile_dataframe(df, dataset_name="test")
        candidates = find_candidate_qis([prof])
        names = [c.column_name for c in candidates]

        assert "age" in names
        assert "const_col" not in names
        assert "null_col" not in names


class TestQISelection:
    """Immutable QISelection operations: confirm, reject, add_manual."""

    def test_selection_workflow(self) -> None:
        prof_a = profile_csv(FIXTURE_A_PATH, dataset_name="A")
        candidates = find_candidate_qis([prof_a])
        selection = QISelection(candidates=candidates)

        # Initially, suggested candidates
        suggested = [
            c.column_name for c in selection.candidates if c.status == "suggested"
        ]
        assert "age" in suggested

        # Confirm 'age'
        s_confirmed = selection.confirm("age")
        assert selection is not s_confirmed  # Pure immutable operation
        c_age = next(c for c in s_confirmed.candidates if c.column_name == "age")
        assert c_age.status == "confirmed"

        # Reject 'age'
        s_rejected = s_confirmed.reject("age")
        r_age = next(c for c in s_rejected.candidates if c.column_name == "age")
        assert r_age.status == "rejected"

        # Add manual candidate 'course'
        s_manual = s_rejected.add_manual("course", dataset_name="A")
        c_course = next(c for c in s_manual.candidates if c.column_name == "course")
        assert c_course.status == "confirmed"
        assert "manually added" in c_course.reasons[0].lower()

        # Selected columns (only confirmed)
        selected_a = s_manual.selected_columns(dataset_name="A")
        assert "course" in selected_a
        assert "age" not in selected_a
