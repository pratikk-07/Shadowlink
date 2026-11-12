"""Unit tests for Equivalence Classes and k-Anonymity (Phase 2).

Hand-verified test oracles and invariants:
- Fixture A on QI [age, city]:
    sizes {2,1,2,2,1} -> sorted [2, 2, 2, 1, 1]
    num_classes = 5
    k = 1
    singleton_record_count = 2 (rows with (21, Kolkata) and (23, Mumbai))
    singleton_record_proportion = 2/8 = 0.25
    discernibility_metric (DM) = 2^2 + 2^2 + 2^2 + 1^2 + 1^2 = 14
- Fixture A on QI [age, city, course]:
    sizes {1,1,1,1,1,2,1} -> sorted [2, 1, 1, 1, 1, 1, 1]
    num_classes = 7
    k = 1
    singleton_record_count = 6
    singleton_record_proportion = 6/8 = 0.75
    discernibility_metric (DM) = 4 + 1 + 1 + 1 + 1 + 1 + 1 = 10
- Simple cases:
    sizes [1, 1, 3] -> k=1, singleton_record_count=2, proportion=2/5=0.4
    sizes [2, 3] -> k=2, singleton_record_count=0, singleton_record_proportion=0.0
- Missing value policy tests ("own_group" vs "exclude_records")
- Validation and invariants (df immutability, sum of class sizes == records_analysed).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shadowlink.common.exceptions import ConfigError, ValidationError
from shadowlink.qi_analyser.equivalence import (
    build_equivalence_classes,
    discernibility_metric,
)

FIXTURE_A_PATH = Path("tests/fixtures/tiny_people_a.csv")


class TestFixtureAEquivalenceClasses:
    """Exact hand-calculated tests on tiny_people_a.csv."""

    def test_fixture_a_age_city(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        result = build_equivalence_classes(df, qi_columns=["age", "city"])

        assert result.qi_columns == ["age", "city"]
        assert result.total_records == 8
        assert result.records_analysed == 8
        assert result.excluded_record_count == 0
        assert result.class_sizes == [2, 2, 2, 1, 1]
        assert result.num_classes == 5
        assert result.k == 1
        assert result.singleton_class_count == 2
        assert result.singleton_record_count == 2
        assert result.singleton_record_proportion == pytest.approx(0.25)

        # Series of class sizes aligned to index
        assert len(result.record_class_sizes) == 8
        assert list(result.record_class_sizes.index) == list(df.index)
        # Verify discernibility metric
        assert discernibility_metric(result) == 14
        assert discernibility_metric(result.class_sizes) == 14

    def test_fixture_a_age_city_course(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        result = build_equivalence_classes(df, qi_columns=["age", "city", "course"])

        assert result.qi_columns == ["age", "city", "course"]
        assert result.total_records == 8
        assert result.records_analysed == 8
        assert result.excluded_record_count == 0
        assert result.class_sizes == [2, 1, 1, 1, 1, 1, 1]
        assert result.num_classes == 7
        assert result.k == 1
        assert result.singleton_class_count == 6
        assert result.singleton_record_count == 6
        assert result.singleton_record_proportion == pytest.approx(0.75)
        assert discernibility_metric(result) == 10


class TestHandCalculatedEquivalenceScenarios:
    """Explicit hand-verified micro test cases."""

    def test_sizes_1_1_3(self) -> None:
        # 5 rows total: values [A, B, C, C, C]
        df = pd.DataFrame({"qi": ["A", "B", "C", "C", "C"]})
        result = build_equivalence_classes(df, qi_columns=["qi"])

        assert result.class_sizes == [3, 1, 1]
        assert result.num_classes == 3
        assert result.k == 1
        assert result.singleton_class_count == 2
        assert result.singleton_record_count == 2
        assert result.singleton_record_proportion == pytest.approx(2 / 5)
        # DM = 3^2 + 1^2 + 1^2 = 9 + 1 + 1 = 11
        assert discernibility_metric(result) == 11

    def test_sizes_2_3(self) -> None:
        # 5 rows total: [X, X, Y, Y, Y] -> k = 2
        df = pd.DataFrame({"qi": ["X", "X", "Y", "Y", "Y"]})
        result = build_equivalence_classes(df, qi_columns=["qi"])

        assert result.class_sizes == [3, 2]
        assert result.num_classes == 2
        assert result.k == 2
        assert result.singleton_class_count == 0
        assert result.singleton_record_count == 0
        assert result.singleton_record_proportion == pytest.approx(0.0)
        # DM = 9 + 4 = 13
        assert discernibility_metric(result) == 13

    def test_singleton_distinction_scenario(self) -> None:
        """Verify distinction between singleton class count and singleton record count.

        In all cases, since each singleton class contains exactly 1 record,
        singleton_record_count == singleton_class_count * 1.
        However, the proportion is over records_analysed (e.g. 2 / 5 vs 2 / 3 classes).
        """
        df = pd.DataFrame({"qi": ["A", "B", "C", "C", "C"]})
        res = build_equivalence_classes(df, ["qi"])
        assert res.singleton_class_count == 2
        assert res.singleton_record_count == 2
        # Class fraction would be 2/3, but record proportion is 2/5 = 0.4
        assert res.singleton_record_proportion == pytest.approx(0.4)


class TestMissingValuePolicies:
    """Test 'own_group' vs 'exclude_records' policies."""

    def test_missing_policy_own_group(self) -> None:
        # 4 records:
        # Row 0: (20, 'Kolkata')
        # Row 1: (20, 'Kolkata')
        # Row 2: (None, 'Kolkata')
        # Row 3: (None, 'Delhi')
        df = pd.DataFrame(
            {
                "age": [20, 20, None, None],
                "city": ["Kolkata", "Kolkata", "Kolkata", "Delhi"],
            }
        )
        result = build_equivalence_classes(
            df, qi_columns=["age", "city"], missing_policy="own_group"
        )
        assert result.total_records == 4
        assert result.records_analysed == 4
        assert result.excluded_record_count == 0
        # Classes: (20, Kolkata)->2, (None, Kolkata)->1, (None, Delhi)->1
        assert result.class_sizes == [2, 1, 1]
        assert result.num_classes == 3
        assert result.k == 1
        assert result.singleton_record_count == 2
        assert result.singleton_record_proportion == pytest.approx(0.5)

    def test_missing_policy_exclude_records(self) -> None:
        df = pd.DataFrame(
            {
                "age": [20, 20, None, None],
                "city": ["Kolkata", "Kolkata", "Kolkata", "Delhi"],
            }
        )
        result = build_equivalence_classes(
            df, qi_columns=["age", "city"], missing_policy="exclude_records"
        )
        assert result.total_records == 4
        assert result.records_analysed == 2
        assert result.excluded_record_count == 2
        # Remaining records: (20, Kolkata) -> 2
        assert result.class_sizes == [2]
        assert result.num_classes == 1
        assert result.k == 2
        assert result.singleton_record_count == 0
        assert result.singleton_record_proportion == pytest.approx(0.0)

    def test_all_missing_exclude_records(self) -> None:
        df = pd.DataFrame({"qi": [None, np.nan, None]})
        result = build_equivalence_classes(
            df, qi_columns=["qi"], missing_policy="exclude_records"
        )
        assert result.total_records == 3
        assert result.records_analysed == 0
        assert result.excluded_record_count == 3
        assert result.class_sizes == []
        assert result.num_classes == 0
        assert result.k is None
        assert result.singleton_class_count == 0
        assert result.singleton_record_count == 0
        assert result.singleton_record_proportion is None


class TestValidationAndEdgeCases:
    """Validation checks on input arguments."""

    def test_forbidden_column_in_dataframe_raises(self) -> None:
        df = pd.DataFrame({"age": [20], "true_id": [1]})
        with pytest.raises(ValidationError, match="forbidden column"):
            build_equivalence_classes(df, qi_columns=["age"])

    def test_empty_qi_columns_raises(self) -> None:
        df = pd.DataFrame({"age": [20, 21]})
        with pytest.raises(ValidationError, match="empty"):
            build_equivalence_classes(df, qi_columns=[])

    def test_unknown_qi_column_raises(self) -> None:
        df = pd.DataFrame({"age": [20, 21]})
        with pytest.raises(ValidationError, match="not found in DataFrame"):
            build_equivalence_classes(df, qi_columns=["age", "salary"])

    def test_duplicate_qi_columns_raises(self) -> None:
        df = pd.DataFrame({"age": [20, 21]})
        with pytest.raises(ValidationError, match="Duplicate column"):
            build_equivalence_classes(df, qi_columns=["age", "age"])

    def test_invalid_missing_policy_raises_config_error(self) -> None:
        df = pd.DataFrame({"age": [20, 21]})
        with pytest.raises(ConfigError, match="Unrecognised missing_policy"):
            build_equivalence_classes(
                df,
                qi_columns=["age"],
                missing_policy="drop_table",  # type: ignore[arg-type]
            )

    def test_zero_rows_dataframe(self) -> None:
        df = pd.DataFrame(columns=["age", "city"])
        result = build_equivalence_classes(df, qi_columns=["age", "city"])
        assert result.total_records == 0
        assert result.records_analysed == 0
        assert result.excluded_record_count == 0
        assert result.class_sizes == []
        assert result.num_classes == 0
        assert result.k is None
        assert result.singleton_record_count == 0
        assert result.singleton_record_proportion is None
        assert discernibility_metric(result) == 0

    def test_discernibility_metric_empty_sequence(self) -> None:
        assert discernibility_metric([]) == 0


class TestInvariantsAndImmutability:
    """Property tests and immutability guarantees."""

    def test_caller_dataframe_not_mutated(self) -> None:
        df = pd.read_csv(FIXTURE_A_PATH)
        df_copy = df.copy(deep=True)
        _ = build_equivalence_classes(df, qi_columns=["age", "city"])
        pd.testing.assert_frame_equal(df, df_copy)

    @pytest.mark.parametrize("seed", [42, 123, 999])
    def test_randomized_invariants(self, seed: int) -> None:
        rng = np.random.default_rng(seed)
        n = 100
        df = pd.DataFrame(
            {
                "age": rng.integers(20, 25, size=n),
                "city": rng.choice(["Delhi", "Mumbai", "Kolkata"], size=n),
                "course": rng.choice(["CSE", "ECE"], size=n),
            }
        )

        result = build_equivalence_classes(df, qi_columns=["age", "city"])

        # Invariant 1: Sum of class sizes equals records analysed
        assert sum(result.class_sizes) == result.records_analysed
        assert result.records_analysed == n

        # Invariant 2: Class sizes are strictly sorted descending
        for i in range(len(result.class_sizes) - 1):
            assert result.class_sizes[i] >= result.class_sizes[i + 1]

        # Invariant 3: k equals the minimum class size
        assert result.k == result.class_sizes[-1]

        # Invariant 4: Sum of record_class_sizes equal sum(size^2) == DM
        expected_dm = sum(s**2 for s in result.class_sizes)
        assert result.record_class_sizes.sum() == expected_dm
        assert discernibility_metric(result) == expected_dm
