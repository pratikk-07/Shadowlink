"""Tests for shadowlink.common.normalization.normalize_column_name.

Hand-verified expected values are stated inline as comments.
Every assertion tests an exact string equality — no approximations needed.
"""

from __future__ import annotations

from shadowlink.common.normalization import normalize_column_name


class TestNormalizeColumnName:
    """Unit tests for normalize_column_name."""

    # ------------------------------------------------------------------
    # Whitespace stripping
    # ------------------------------------------------------------------

    def test_strips_leading_space(self) -> None:
        # " age" -> strip -> "age" -> lower -> "age" -> collapse -> "age"
        assert normalize_column_name(" age") == "age"

    def test_strips_trailing_space(self) -> None:
        assert normalize_column_name("age ") == "age"

    def test_strips_both_sides(self) -> None:
        assert normalize_column_name("  age  ") == "age"

    def test_strips_tab(self) -> None:
        assert normalize_column_name("\tage\t") == "age"

    def test_strips_newline(self) -> None:
        assert normalize_column_name("\nage\n") == "age"

    # ------------------------------------------------------------------
    # Case folding
    # ------------------------------------------------------------------

    def test_lowercases_all_caps(self) -> None:
        assert normalize_column_name("AGE") == "age"

    def test_lowercases_mixed_case(self) -> None:
        assert normalize_column_name("CiTy") == "city"

    def test_already_lowercase_unchanged(self) -> None:
        assert normalize_column_name("age") == "age"

    # ------------------------------------------------------------------
    # Inner whitespace collapsing
    # ------------------------------------------------------------------

    def test_collapses_double_space(self) -> None:
        # "first  name" -> collapse -> "first name"
        assert normalize_column_name("first  name") == "first name"

    def test_collapses_multiple_spaces(self) -> None:
        assert normalize_column_name("first   name") == "first name"

    def test_collapses_inner_tab(self) -> None:
        assert normalize_column_name("first\tname") == "first name"

    def test_collapses_mixed_inner_whitespace(self) -> None:
        assert normalize_column_name("first \t name") == "first name"

    # ------------------------------------------------------------------
    # Combined: strip + lowercase + collapse
    # ------------------------------------------------------------------

    def test_fixture_b_age_column(self) -> None:
        """Fixture B header ' Age ' must normalise to 'age'."""
        # ' Age ' -> strip -> 'Age' -> lower -> 'age' -> collapse -> 'age'
        assert normalize_column_name(" Age ") == "age"

    def test_fixture_b_city_column(self) -> None:
        """Fixture B header 'CITY' must normalise to 'city'."""
        assert normalize_column_name("CITY") == "city"

    def test_fixture_b_location_column(self) -> None:
        """Fixture B 'location' is already clean."""
        assert normalize_column_name("location") == "location"

    def test_fixture_b_timestamp_column(self) -> None:
        assert normalize_column_name("timestamp") == "timestamp"

    def test_all_transformations_combined(self) -> None:
        # "  First   Name  " -> strip -> "First   Name" -> lower ->
        # "first   name" -> collapse -> "first name"
        assert normalize_column_name("  First   Name  ") == "first name"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_string(self) -> None:
        # An empty string stays empty.
        assert normalize_column_name("") == ""

    def test_only_spaces(self) -> None:
        # Stripping "   " gives "" -> lower -> "" -> collapse -> ""
        assert normalize_column_name("   ") == ""

    def test_single_character(self) -> None:
        assert normalize_column_name("A") == "a"

    def test_numbers_in_name(self) -> None:
        # Digits are preserved; only whitespace and case are transformed.
        assert normalize_column_name(" Col1 ") == "col1"

    def test_unicode_letters(self) -> None:
        # lower() works on unicode letters (e.g. accented).
        assert normalize_column_name("Âge") == "âge"
