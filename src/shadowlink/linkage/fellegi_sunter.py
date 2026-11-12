"""Fellegi-Sunter probabilistic record linkage implementation."""

from __future__ import annotations

import math
from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import ConfigError, ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.linkage.comparators import (
    exact_comparator,
    jaro_similarity,
    jaro_winkler_similarity,
    levenshtein_similarity,
    numeric_comparator,
    time_comparator,
)
from shadowlink.linkage.models import AttributeComparatorSpec, FellegiSunterParams


def _get_similarity(
    val1: object,
    val2: object,
    spec: AttributeComparatorSpec,
) -> float | None:
    m = spec.method
    p = spec.parameters
    if m == "exact":
        return exact_comparator(val1, val2)
    if m == "numeric":
        return numeric_comparator(val1, val2, tolerance=float(p.get("tolerance", 0.0)))
    if m == "time":
        return time_comparator(
            val1, val2, window_minutes=float(p.get("window_minutes", 0.0))
        )
    if m == "levenshtein":
        return levenshtein_similarity(val1, val2)
    if m == "jaro":
        return jaro_similarity(val1, val2)
    if m == "jaro_winkler":
        return jaro_winkler_similarity(
            val1,
            val2,
            p=float(p.get("p", 0.1)),
            max_p=int(p.get("max_p", 4)),
        )
    return None


def fellegi_sunter_linkage(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    candidate_pairs: pd.DataFrame,
    specs: Sequence[AttributeComparatorSpec],
    params: FellegiSunterParams,
    lower_threshold: float,
    upper_threshold: float,
    left_name: str = "left",
    right_name: str = "right",
    left_id_col: str = "record_id",
    right_id_col: str = "record_id",
) -> pd.DataFrame:
    """Score candidate pairs using Fellegi-Sunter weight of evidence theory.

    Weights:
    - Agreement weight = log2(m_i / u_i)
    - Disagreement weight = log2((1 - m_i) / (1 - u_i))
    - Missing comparison contributes 0.0
    Score = sum of weights across attributes.

    Decision rules:
    - score >= upper_threshold -> 'match'
    - score <= lower_threshold -> 'non_match'
    - otherwise -> 'possible'
    """
    validate_no_forbidden_columns(left_df)
    validate_no_forbidden_columns(right_df)

    if lower_threshold > upper_threshold:
        raise ValidationError(
            f"lower_threshold ({lower_threshold}) cannot exceed "
            f"upper_threshold ({upper_threshold})."
        )
    if not specs:
        raise ValidationError("At least one AttributeComparatorSpec must be provided.")

    # Validate probabilities
    weights_agree: dict[str, float] = {}
    weights_disagree: dict[str, float] = {}
    for s in specs:
        attr = s.attribute
        if attr not in params.m_probabilities or attr not in params.u_probabilities:
            raise ConfigError(
                f"Missing probability for attribute '{attr}' in FellegiSunterParams."
            )
        m = params.m_probabilities[attr]
        u = params.u_probabilities[attr]
        if not (0.0 < m < 1.0) or not (0.0 < u < 1.0):
            raise ConfigError(
                f"Probabilities for '{attr}' must be in (0, 1), got m={m}, u={u}."
            )
        weights_agree[attr] = math.log2(m / u)
        weights_disagree[attr] = math.log2((1.0 - m) / (1.0 - u))

    left_indexed = left_df.set_index(left_id_col)
    right_indexed = right_df.set_index(right_id_col)

    records: list[dict[str, object]] = []
    for _, pair in candidate_pairs.iterrows():
        l_id = pair["left_id"]
        r_id = pair["right_id"]

        l_row = left_indexed.loc[l_id]
        r_row = right_indexed.loc[r_id]

        pair_score = 0.0
        row_dict: dict[str, object] = {
            "left_dataset": left_name,
            "left_id": l_id,
            "right_dataset": right_name,
            "right_id": r_id,
        }

        for s in specs:
            attr = s.attribute
            val1 = l_row.get(attr)
            val2 = r_row.get(attr)
            sim = _get_similarity(val1, val2, s)
            row_dict[f"sim_{attr}"] = sim

            if sim is None:
                # Missing comparison contributes 0.0 weight
                continue

            if sim >= s.agreement_threshold:
                pair_score += weights_agree[attr]
            else:
                pair_score += weights_disagree[attr]

        if pair_score >= upper_threshold:
            decision = "match"
        elif pair_score <= lower_threshold:
            decision = "non_match"
        else:
            decision = "possible"

        row_dict["score"] = float(pair_score)
        row_dict["decision"] = decision
        row_dict["method"] = "fellegi_sunter"
        records.append(row_dict)

    return pd.DataFrame(records)
