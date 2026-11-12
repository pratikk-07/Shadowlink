"""Evaluation metrics for record linkage, blocking, and re-identification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.evaluator.ground_truth import build_true_pairs


@dataclass(frozen=True)
class LinkageEvaluation:
    """Linkage quality metrics evaluated against ground truth."""

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    f1_score: float | None


@dataclass(frozen=True)
class BlockingEvaluation:
    """Quality and completeness of candidate pair blocking."""

    reduction_ratio: float
    pairs_completeness: float | None
    retained_true_pairs: int
    total_true_pairs: int


@dataclass(frozen=True)
class ReidentificationMetrics:
    """Re-identification success under deterministic and tie-adjusted policies."""

    evaluated_targets_count: int
    deterministic_success_rate: float
    tie_adjusted_success_rate: float


def evaluate_linkage_predictions(
    predicted_pairs: pd.DataFrame,
    true_pairs: set[tuple[str, str]],
    total_true_pairs: int | None = None,
) -> LinkageEvaluation:
    """Evaluate predicted match pairs against ground truth.

    Parameters
    ----------
    predicted_pairs:
        Scored candidate pairs DataFrame with 'decision', 'left_id', 'right_id'.
    true_pairs:
        Ground truth set of matching (left_id, right_id) tuples.
    total_true_pairs:
        Total true pairs in universe (including those dropped by blocking).
        If omitted, defaults to len(true_pairs).
    """
    matches = predicted_pairs[predicted_pairs["decision"] == "match"]
    l_ids = matches["left_id"].astype(str)
    r_ids = matches["right_id"].astype(str)
    predicted_set = set(zip(l_ids, r_ids))

    tp = len(predicted_set.intersection(true_pairs))
    fp = len(predicted_set - true_pairs)

    total_truth = total_true_pairs if total_true_pairs is not None else len(true_pairs)
    fn = max(0, total_truth - tp)

    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else None
    rec = float(tp / total_truth) if total_truth > 0 else None
    if prec is not None and rec is not None and (prec + rec) > 0:
        f1 = float(2.0 * prec * rec / (prec + rec))
    else:
        f1 = None

    return LinkageEvaluation(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=prec,
        recall=rec,
        f1_score=f1,
    )


def evaluate_blocking(
    candidate_pairs: pd.DataFrame,
    all_true_pairs: set[tuple[str, str]],
    naive_comparisons: int,
) -> BlockingEvaluation:
    """Evaluate reduction ratio and pairs completeness of candidate pair blocking."""
    c_l = candidate_pairs["left_id"].astype(str)
    c_r = candidate_pairs["right_id"].astype(str)
    candidate_set = set(zip(c_l, c_r))
    retained_true = len(candidate_set.intersection(all_true_pairs))
    total_true = len(all_true_pairs)

    reduction = (
        1.0 - (len(candidate_set) / naive_comparisons) if naive_comparisons > 0 else 0.0
    )
    completeness = float(retained_true / total_true) if total_true > 0 else None

    return BlockingEvaluation(
        reduction_ratio=float(reduction),
        pairs_completeness=completeness,
        retained_true_pairs=retained_true,
        total_true_pairs=total_true,
    )


def reidentification_success_rate(
    scored_pairs: pd.DataFrame,
    truth: pd.DataFrame,
    left_dataset: str,
    right_dataset: str,
    targets: Sequence[str] | None = None,
) -> ReidentificationMetrics:
    """Compute deterministic and tie-adjusted re-identification success rates.

    Targets whose true counterpart is not present in right_dataset are excluded
    from the denominator.
    """
    true_pairs = build_true_pairs(truth, left_dataset, right_dataset)
    target_to_true_right = dict(true_pairs)

    # Filter targets present in truth for left_dataset that have a right counterpart
    if targets is not None:
        eval_targets = [t for t in targets if t in target_to_true_right]
    else:
        eval_targets = list(target_to_true_right.keys())

    if not eval_targets:
        raise ValidationError("No valid targets with ground-truth counterpart found.")

    det_credits: list[float] = []
    tie_credits: list[float] = []

    pairs_by_left = scored_pairs.groupby("left_id")

    for t_id in eval_targets:
        true_right = target_to_true_right[t_id]

        if t_id not in pairs_by_left.groups:
            # Not linked / dropped
            det_credits.append(0.0)
            tie_credits.append(0.0)
            continue

        group = pairs_by_left.get_group(t_id)
        max_score = group["score"].max()
        top_candidates = group[group["score"] == max_score]

        top_right_ids = sorted(top_candidates["right_id"].astype(str).tolist())
        g_size = len(top_right_ids)

        # Tie-adjusted: 1 / g if true record is in top tie group, else 0
        if true_right in top_right_ids:
            tie_credits.append(1.0 / g_size)
        else:
            tie_credits.append(0.0)

        # Deterministic: tie-break by lowest right_id alphabetically
        deterministic_pick = top_right_ids[0]
        if deterministic_pick == true_right:
            det_credits.append(1.0)
        else:
            det_credits.append(0.0)

    n_eval = len(eval_targets)
    return ReidentificationMetrics(
        evaluated_targets_count=n_eval,
        deterministic_success_rate=float(sum(det_credits) / n_eval),
        tie_adjusted_success_rate=float(sum(tie_credits) / n_eval),
    )
