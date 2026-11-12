"""Calibration of Fellegi-Sunter parameters from labeled ground-truth training data."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from shadowlink.evaluator.ground_truth import build_true_pairs
from shadowlink.linkage.comparators import exact_comparator
from shadowlink.linkage.models import FellegiSunterParams


def estimate_m_u_from_ground_truth(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    candidate_pairs: pd.DataFrame,
    truth: pd.DataFrame,
    left_dataset: str,
    right_dataset: str,
    attributes: Sequence[str],
    agreement_threshold: float = 0.85,
    smoothing: float = 1.0,
    left_id_col: str = "record_id",
    right_id_col: str = "record_id",
) -> FellegiSunterParams:
    """Calibrate m and u probabilities using ground truth with Laplace smoothing.

    Formulas:
        m_i = P(agree_i | true match) ≈ (N_agree,M + smoothing) / (N_M + 2 * smoothing)
        u_i = P(agree_i | non-match) ≈ (N_agree,U + smoothing) / (N_U + 2 * smoothing)

    Guarantees 0 < m_i, u_i < 1. Handed as pure values to linkage engine.
    """
    true_pairs = build_true_pairs(truth, left_dataset, right_dataset)
    left_indexed = left_df.set_index(left_id_col)
    right_indexed = right_df.set_index(right_id_col)

    n_matches = 0
    n_non_matches = 0
    agree_matches: dict[str, int] = {attr: 0 for attr in attributes}
    agree_non_matches: dict[str, int] = {attr: 0 for attr in attributes}

    for _, row in candidate_pairs.iterrows():
        l_id = str(row["left_id"])
        r_id = str(row["right_id"])
        is_match = (l_id, r_id) in true_pairs

        if is_match:
            n_matches += 1
        else:
            n_non_matches += 1

        l_row = left_indexed.loc[l_id]
        r_row = right_indexed.loc[r_id]

        for attr in attributes:
            val1 = l_row.get(attr)
            val2 = r_row.get(attr)
            sim = exact_comparator(val1, val2)

            agrees = sim is not None and sim >= agreement_threshold
            if agrees:
                if is_match:
                    agree_matches[attr] += 1
                else:
                    agree_non_matches[attr] += 1

    m_probs: dict[str, float] = {}
    u_probs: dict[str, float] = {}

    for attr in attributes:
        m = (agree_matches[attr] + smoothing) / (n_matches + 2.0 * smoothing)
        u = (agree_non_matches[attr] + smoothing) / (n_non_matches + 2.0 * smoothing)
        # Clamp strictly inside (0.001, 0.999) to satisfy Fellegi-Sunter validity
        m_probs[attr] = max(0.001, min(0.999, float(m)))
        u_probs[attr] = max(0.001, min(0.999, float(u)))

    return FellegiSunterParams(m_probabilities=m_probs, u_probabilities=u_probs)

