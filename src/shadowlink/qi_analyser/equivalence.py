"""Equivalence class generation and k-anonymity measurement."""

from __future__ import annotations

from typing import Sequence, cast

import pandas as pd

from shadowlink.common.exceptions import ConfigError, ValidationError
from shadowlink.common.validation import (
    validate_hashable_values,
    validate_no_duplicate_columns,
    validate_no_forbidden_columns,
)
from shadowlink.qi_analyser.models import EquivalenceClassResult, MissingPolicy

VALID_MISSING_POLICIES = frozenset({"own_group", "exclude_records"})


def discernibility_metric(
    classes: EquivalenceClassResult | Sequence[int],
) -> int:
    """Calculate the Discernibility Metric (DM = sum(f_i^2)).

    Parameters
    ----------
    classes:
        Either an EquivalenceClassResult instance or a sequence of class sizes.

    Returns
    -------
    int
        Discernibility metric score.
    """
    if isinstance(classes, EquivalenceClassResult):
        sizes: Sequence[int] = classes.class_sizes
    else:
        sizes = classes

    return int(sum(size**2 for size in sizes))


def build_equivalence_classes(
    df: pd.DataFrame,
    qi_columns: Sequence[str],
    missing_policy: MissingPolicy = "own_group",
) -> EquivalenceClassResult:
    """Group DataFrame by quasi-identifiers into equivalence classes.

    Parameters
    ----------
    df:
        Input DataFrame to partition. Never mutated.
    qi_columns:
        List of quasi-identifier column names to group on.
    missing_policy:
        'own_group' (missing values form distinct groups) or
        'exclude_records' (records with any missing QI are excluded).

    Returns
    -------
    EquivalenceClassResult
    """
    # Defensive validations on df
    validate_no_forbidden_columns(df)
    validate_no_duplicate_columns(df)
    validate_hashable_values(df)

    if not qi_columns:
        raise ValidationError(
            "qi_columns list cannot be empty. "
            "Specify at least one quasi-identifier column."
        )

    if len(qi_columns) != len(set(qi_columns)):
        raise ValidationError(
            f"Duplicate column names in qi_columns: {list(qi_columns)}. "
            "Each quasi-identifier must be listed only once."
        )

    missing_cols = [c for c in qi_columns if c not in df.columns]
    if missing_cols:
        raise ValidationError(
            f"Specified quasi-identifier column(s) not found in DataFrame: "
            f"{missing_cols}. Available columns: {list(df.columns)}."
        )

    if missing_policy not in VALID_MISSING_POLICIES:
        raise ConfigError(
            f"Unrecognised missing_policy '{missing_policy}'. "
            f"Must be one of: {sorted(VALID_MISSING_POLICIES)}."
        )

    total_records = len(df)
    cols_to_group = list(qi_columns)

    if total_records == 0:
        return EquivalenceClassResult(
            qi_columns=cols_to_group,
            total_records=0,
            records_analysed=0,
            excluded_record_count=0,
            class_sizes=[],
            num_classes=0,
            k=None,
            singleton_class_count=0,
            singleton_record_count=0,
            singleton_record_proportion=None,
            record_class_sizes=pd.Series([], dtype="int64", index=df.index),
            missing_policy=missing_policy,
        )

    # Handle missing values policy
    if missing_policy == "exclude_records":
        mask_valid = ~df[cols_to_group].isna().any(axis=1)
        analysed_df = df.loc[mask_valid, cols_to_group]
        excluded_count = total_records - int(mask_valid.sum())
    else:
        analysed_df = df[cols_to_group]
        excluded_count = 0

    records_analysed = len(analysed_df)

    if records_analysed == 0:
        # All records were excluded due to missing values
        return EquivalenceClassResult(
            qi_columns=cols_to_group,
            total_records=total_records,
            records_analysed=0,
            excluded_record_count=excluded_count,
            class_sizes=[],
            num_classes=0,
            k=None,
            singleton_class_count=0,
            singleton_record_count=0,
            singleton_record_proportion=None,
            record_class_sizes=pd.Series(
                [0] * total_records, dtype="int64", index=df.index
            ),
            missing_policy=missing_policy,
        )

    # In 'own_group', dropna=False ensures NaN creates distinct groups in groupby
    # For multiple columns, dropna=False handles tuples with NaN
    grouped = analysed_df.groupby(cols_to_group, dropna=False, observed=False)
    # Series of group sizes aligned to analysed_df index
    transform_sizes = cast(pd.Series, grouped[cols_to_group[0]].transform("size"))

    # Series aligned to full input df.index
    if missing_policy == "exclude_records":
        full_record_sizes = pd.Series(0, index=df.index, dtype="int64")
        full_record_sizes.loc[analysed_df.index] = transform_sizes
    else:
        full_record_sizes = transform_sizes.astype("int64")

    # Distinct class sizes sorted descending
    group_counts: list[int] = grouped.size().tolist()
    group_counts.sort(reverse=True)

    num_classes = len(group_counts)
    k_val = int(group_counts[-1]) if group_counts else None

    # Count singletons
    singleton_classes = sum(1 for size in group_counts if size == 1)
    singleton_records = singleton_classes  # Each singleton class has 1 record
    singleton_prop = (
        (singleton_records / records_analysed) if records_analysed > 0 else None
    )

    return EquivalenceClassResult(
        qi_columns=cols_to_group,
        total_records=total_records,
        records_analysed=records_analysed,
        excluded_record_count=excluded_count,
        class_sizes=group_counts,
        num_classes=num_classes,
        k=k_val,
        singleton_class_count=singleton_classes,
        singleton_record_count=singleton_records,
        singleton_record_proportion=singleton_prop,
        record_class_sizes=full_record_sizes,
        missing_policy=missing_policy,
    )
