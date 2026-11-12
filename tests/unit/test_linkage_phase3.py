"""Unit tests for Phase 3 Linkage: preprocessing, comparators, and blocking."""

from __future__ import annotations

import pandas as pd
import pytest

from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.comparators import (
    exact_comparator,
    jaro_similarity,
    jaro_winkler_similarity,
    levenshtein_distance,
    levenshtein_similarity,
    numeric_comparator,
    time_comparator,
)
from shadowlink.linkage.preprocessing import preprocess_linkage_frame, standardize_text


class TestPreprocessing:
    def test_standardize_text(self) -> None:
        assert standardize_text("  Kolkata  ") == "kolkata"
        assert standardize_text("DELHI\tCITY") == "delhi city"
        assert standardize_text(None) is None
        assert standardize_text("") is None

    def test_preprocess_linkage_frame(self) -> None:
        df = pd.DataFrame(
            {
                " City ": ["  KOLKATA "],
                "Timestamp": ["2026-01-01 10:00:00"],
            }
        )
        clean = preprocess_linkage_frame(
            df, text_columns=["city"], datetime_columns=["timestamp"]
        )
        assert "city" in clean.columns
        assert "timestamp" in clean.columns
        assert clean["city"].iloc[0] == "kolkata"


class TestComparators:
    def test_levenshtein_test_vectors(self) -> None:
        """Test vectors:

        kitten/sitting=3, flaw/lawn=2, ""/abc=3, same/same=0
        """
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("flaw", "lawn") == 2
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("same", "same") == 0

    def test_jaro_test_vectors(self) -> None:
        """Test vectors:

        MARTHA/MARHTA=0.9444, DWAYNE/DUANE=0.8222, DIXON/DICKSONX=0.7667
        """
        assert jaro_similarity("MARTHA", "MARHTA") == pytest.approx(0.9444, abs=1e-4)
        assert jaro_similarity("DWAYNE", "DUANE") == pytest.approx(0.8222, abs=1e-4)
        assert jaro_similarity("DIXON", "DICKSONX") == pytest.approx(0.7667, abs=1e-4)

    def test_jaro_winkler_test_vectors(self) -> None:
        """Test vectors:

        MARTHA/MARHTA=0.9611, DWAYNE/DUANE=0.8400, DIXON/DICKSONX=0.8133
        """
        jw = jaro_winkler_similarity
        assert jw("MARTHA", "MARHTA") == pytest.approx(0.9611, abs=1e-4)
        assert jw("DWAYNE", "DUANE") == pytest.approx(0.8400, abs=1e-4)
        assert jw("DIXON", "DICKSONX") == pytest.approx(0.8133, abs=1e-4)

    def test_comparator_symmetry_and_identity(self) -> None:
        s1, s2 = "Kolkata", "Kolakta"
        assert jaro_similarity(s1, s2) == pytest.approx(jaro_similarity(s2, s1))  # type: ignore[arg-type]
        assert jaro_similarity(s1, s1) == 1.0
        assert jaro_winkler_similarity(s1, s1) == 1.0
        assert levenshtein_similarity(s1, s1) == 1.0
        assert exact_comparator(s1, s1) == 1.0

    def test_numeric_and_time_comparators(self) -> None:
        assert numeric_comparator(20, 20, tolerance=2.0) == 1.0
        assert numeric_comparator(20, 21, tolerance=2.0) == 0.5
        assert numeric_comparator(20, 23, tolerance=2.0) == 0.0
        assert numeric_comparator(20, None) is None

        t1 = "2026-01-01 10:00:00"
        t2 = "2026-01-01 10:15:00"
        assert time_comparator(t1, t2, window_minutes=30.0) == 0.5
        assert time_comparator(t1, t2, window_minutes=10.0) == 0.0


class TestBlocking:
    def test_blocking_hand_example(self) -> None:
        """Hand example from spec:

        Left cities [K,K,D,D], right [K,D,D], block on city
        -> 2 + 4 = 6 pairs of 12, reduction ratio 0.5.
        """
        left = pd.DataFrame(
            {
                "record_id": ["L1", "L2", "L3", "L4"],
                "city": ["K", "K", "D", "D"],
            }
        )
        right = pd.DataFrame(
            {
                "record_id": ["R1", "R2", "R3"],
                "city": ["K", "D", "D"],
            }
        )

        pairs_df, report = generate_candidate_pairs(
            left, right, passes=[BlockingPass(columns=["city"])]
        )

        assert report.naive_comparisons == 12
        assert report.candidate_pairs_count == 6
        assert report.reduction_ratio == pytest.approx(0.5)
        assert len(pairs_df) == 6

        # Expected pairs:
        # L1-R1, L2-R1 (city K)
        # L3-R2, L3-R3, L4-R2, L4-R3 (city D)
        expected_pairs = {
            ("L1", "R1"),
            ("L2", "R1"),
            ("L3", "R2"),
            ("L3", "R3"),
            ("L4", "R2"),
            ("L4", "R3"),
        }
        actual_pairs = set(zip(pairs_df["left_id"], pairs_df["right_id"]))
        assert actual_pairs == expected_pairs

    def test_missing_blocking_value_excluded(self) -> None:
        left = pd.DataFrame({"record_id": ["L1"], "city": [None]})
        right = pd.DataFrame({"record_id": ["R1"], "city": ["Kolkata"]})
        pairs_df, report = generate_candidate_pairs(
            left, right, passes=[BlockingPass(columns=["city"])]
        )
        assert report.candidate_pairs_count == 0
        assert len(pairs_df) == 0
