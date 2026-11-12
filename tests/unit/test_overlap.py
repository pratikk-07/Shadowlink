"""Unit tests for shared attribute discovery and overlap mapping (Phase 4).

Covers:
- find_shared_attributes on Fixtures A + B:
    - age in A ('age') and B (' Age ') normalise to 'age'
    - city in A ('city') and B ('CITY') normalise to 'city'
    - location and timestamp only in B
    - course only in A
- Type compatibility check
- Error when 2 columns in SAME dataset normalise to same name -> ValidationError
- calculate_overlap_indicators pairwise shared attribute count and fraction
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from shadowlink.common.exceptions import ValidationError
from shadowlink.profiler.profiler import profile_csv, profile_dataframe
from shadowlink.qi_analyser.overlap import (
    calculate_overlap_indicators,
    find_shared_attributes,
)

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")
FIXTURE_B_PATH = Path("tests/fixtures/tiny_people_b.csv")


class TestFindSharedAttributes:
    """Discovery of overlapping attributes across multiple dataset profiles."""

    def test_shared_attributes_fixtures_a_and_b(self) -> None:
        prof_a = profile_csv(FIXTURE_A_PATH, dataset_name="A")
        prof_b = profile_csv(FIXTURE_B_PATH, dataset_name="B")

        shared_map = find_shared_attributes([prof_a, prof_b])

        # Overlapping attributes: 'age' and 'city'
        canonical_names = list(shared_map.keys())
        assert "age" in canonical_names
        assert "city" in canonical_names
        assert "course" not in canonical_names
        assert "location" not in canonical_names
        assert "timestamp" not in canonical_names

        # Inspect 'age' entry
        age_entries = shared_map["age"]
        assert len(age_entries) == 2
        entry_a = next(e for e in age_entries if e.dataset_name == "A")
        entry_b = next(e for e in age_entries if e.dataset_name == "B")

        assert entry_a.original_name == "age"
        assert entry_b.original_name == " Age "  # Preserved original from B
        assert entry_a.kind == "numeric"
        assert entry_b.kind == "numeric"
        assert entry_a.dtype_compatible

        # Inspect 'city' entry
        city_entries = shared_map["city"]
        entry_b_city = next(e for e in city_entries if e.dataset_name == "B")
        assert entry_b_city.original_name == "CITY"

    def test_same_dataset_normalisation_collision_raises(self) -> None:
        # Two columns in the SAME dataset normalizing to the same string
        df = pd.DataFrame([[1, 2]], columns=["First Name", "first  name"])
        prof = profile_dataframe(df, dataset_name="colliding")
        with pytest.raises(
            ValidationError, match="normalize to the same canonical name"
        ):
            find_shared_attributes([prof])


class TestOverlapIndicators:
    """Pairwise overlap statistics between datasets."""

    def test_overlap_indicators_fixtures_a_and_b(self) -> None:
        prof_a = profile_csv(FIXTURE_A_PATH, dataset_name="A")  # 3 cols
        prof_b = profile_csv(FIXTURE_B_PATH, dataset_name="B")  # 4 cols

        shared_map = find_shared_attributes([prof_a, prof_b])
        overlap_report = calculate_overlap_indicators(shared_map, [prof_a, prof_b])

        # 1 pair: (A, B)
        assert len(overlap_report.pairs) == 1
        pair = overlap_report.pairs[0]
        assert (pair.dataset_a, pair.dataset_b) in [("A", "B"), ("B", "A")]
        assert pair.shared_column_count == 2  # age, city

        # Fraction of columns
        if pair.dataset_a == "A":
            assert pair.fraction_of_a == pytest.approx(2 / 3)  # 2 of 3
            assert pair.fraction_of_b == pytest.approx(2 / 4)  # 2 of 4
        else:
            assert pair.fraction_of_a == pytest.approx(2 / 4)
            assert pair.fraction_of_b == pytest.approx(2 / 3)
