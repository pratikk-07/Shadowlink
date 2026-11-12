"""Deterministic and similarity-based record linkage methods, plus match ranking."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.linkage.comparators import exact_comparator
from shadowlink.linkage.fellegi_sunter import _get_similarity
from shadowlink.linkage.models import AttributeComparatorSpec


def deterministic_linkage(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    candidate_pairs: pd.DataFrame,
    attributes: Sequence[str],
    left_name: str = "left",
    right_name: str = "right",
    left_id_col: str = "record_id",
    right_id_col: str = "record_id",
) -> pd.DataFrame:
    """Deterministic exact-match linkage.

    Match iff exact agreement on all chosen attributes (any missing value = no match).
    """
    validate_no_forbidden_columns(left_df)
    validate_no_forbidden_columns(right_df)
    if not attributes:
        raise ValidationError("Attributes sequence cannot be empty.")

    left_indexed = left_df.set_index(left_id_col)
    right_indexed = right_df.set_index(right_id_col)

    records: list[dict[str, object]] = []
    for _, pair in candidate_pairs.iterrows():
        l_id = pair["left_id"]
        r_id = pair["right_id"]

        l_row = left_indexed.loc[l_id]
        r_row = right_indexed.loc[r_id]

        row_dict: dict[str, object] = {
            "left_dataset": left_name,
            "left_id": l_id,
            "right_dataset": right_name,
            "right_id": r_id,
        }

        agreed = 0
        all_match = True
        for attr in attributes:
            val1 = l_row.get(attr)
            val2 = r_row.get(attr)
            sim = exact_comparator(val1, val2)
            row_dict[f"sim_{attr}"] = sim

            if sim == 1.0:
                agreed += 1
            else:
                all_match = False

        score = float(agreed / len(attributes))
        row_dict["score"] = score
        row_dict["decision"] = "match" if all_match else "non_match"
        row_dict["method"] = "deterministic"
        records.append(row_dict)

    return pd.DataFrame(records)


def similarity_linkage(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    candidate_pairs: pd.DataFrame,
    specs: Sequence[AttributeComparatorSpec],
    threshold: float = 0.8,
    left_name: str = "left",
    right_name: str = "right",
    left_id_col: str = "record_id",
    right_id_col: str = "record_id",
) -> pd.DataFrame:
    """Weighted similarity record linkage.

    Weights are dynamically normalized over non-missing attributes.
    If all attributes are missing, similarity is 0.0.
    """
    validate_no_forbidden_columns(left_df)
    validate_no_forbidden_columns(right_df)
    if not specs:
        raise ValidationError("At least one AttributeComparatorSpec must be provided.")
    if not (0.0 <= threshold <= 1.0):
        raise ValidationError(f"Threshold must be in [0, 1], got {threshold}.")

    left_indexed = left_df.set_index(left_id_col)
    right_indexed = right_df.set_index(right_id_col)

    records: list[dict[str, object]] = []
    for _, pair in candidate_pairs.iterrows():
        l_id = pair["left_id"]
        r_id = pair["right_id"]

        l_row = left_indexed.loc[l_id]
        r_row = right_indexed.loc[r_id]

        row_dict: dict[str, object] = {
            "left_dataset": left_name,
            "left_id": l_id,
            "right_dataset": right_name,
            "right_id": r_id,
        }

        weighted_sum = 0.0
        avail_weights = 0.0
        for s in specs:
            attr = s.attribute
            val1 = l_row.get(attr)
            val2 = r_row.get(attr)
            sim = _get_similarity(val1, val2, s)
            row_dict[f"sim_{attr}"] = sim

            if sim is not None:
                weighted_sum += s.weight * sim
                avail_weights += s.weight

        score = (weighted_sum / avail_weights) if avail_weights > 0.0 else 0.0
        row_dict["score"] = float(score)
        row_dict["decision"] = "match" if score >= threshold else "non_match"
        row_dict["method"] = "similarity"
        records.append(row_dict)

    return pd.DataFrame(records)


def best_match_per_record(scored_pairs: pd.DataFrame) -> pd.DataFrame:
    """Rank candidates per left record by score descending.

    Deterministic tie-break by right_id ascending. Exposes tie group size.
    """
    if scored_pairs.empty:
        return scored_pairs.copy()

    df = scored_pairs.copy(deep=True)

    # Sort deterministically: left_id asc, score desc, right_id asc
    df = df.sort_values(
        by=["left_id", "score", "right_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)

    ranks: list[int] = []
    tie_sizes: list[int] = []

    for _, group in df.groupby("left_id", sort=False):
        top_score = group["score"].iloc[0]
        tie_count = int((group["score"] == top_score).sum())

        g_len = len(group)
        ranks.extend(range(1, g_len + 1))
        # Top ties share the tie group size; non-top ties report 1
        for i in range(g_len):
            tie_sizes.append(tie_count if i < tie_count else 1)

    df["rank"] = ranks
    df["tie_group_size"] = tie_sizes
    return df

