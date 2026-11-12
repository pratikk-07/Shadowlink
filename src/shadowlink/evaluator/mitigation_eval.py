"""Mitigation evaluation against linkage attacks and privacy-utility tradeoffs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from shadowlink.evaluator.ground_truth import build_true_pairs
from shadowlink.evaluator.metrics import evaluate_linkage_predictions
from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.methods import similarity_linkage
from shadowlink.linkage.models import AttributeComparatorSpec
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.metrics import calculate_class_risk


@dataclass(frozen=True)
class MitigationTradeoffReport:
    """Summary of privacy risk and linkage accuracy before vs after mitigation.

    Assumes a worst-case attacker whose auxiliary knowledge undergoes the
    exact same mitigation transformations.
    """

    mitigation_name: str
    baseline_max_risk: float
    mitigated_max_risk: float
    baseline_mean_risk: float
    mitigated_mean_risk: float
    baseline_uniqueness: float
    mitigated_uniqueness: float
    baseline_linkage_f1: float
    mitigated_linkage_f1: float
    utility_loss: float


def evaluate_mitigation_on_dataset(
    original_df: pd.DataFrame,
    mitigated_df: pd.DataFrame,
    qi_columns: Sequence[str],
    mitigation_name: str = "mitigated",
) -> dict[str, float]:
    """Calculate class risk metrics before and after mitigation on a dataset."""
    eq_orig = build_equivalence_classes(original_df, qi_columns=qi_columns)
    risk_orig = calculate_class_risk(eq_orig)
    orig_map = {m.name: m.value for m in risk_orig.metrics}

    eq_mit = build_equivalence_classes(mitigated_df, qi_columns=qi_columns)
    risk_mit = calculate_class_risk(eq_mit)
    mit_map = {m.name: m.value for m in risk_mit.metrics}

    # Utility loss: proportion of non-id cells that differ
    common_cols = [
        c for c in original_df.columns if c in mitigated_df.columns and c != "record_id"
    ]
    diff_cells = 0
    total_cells = len(original_df) * max(1, len(common_cols))
    for c in common_cols:
        s1 = original_df[c].astype(str)
        s2 = mitigated_df[c].astype(str)
        diff_cells += int((s1 != s2).sum())

    utility_loss = diff_cells / total_cells if total_cells > 0 else 0.0

    return {
        "baseline_max_risk": float(orig_map.get("max_class_risk") or 0.0),
        "mitigated_max_risk": float(mit_map.get("max_class_risk") or 0.0),
        "baseline_mean_risk": float(orig_map.get("average_class_risk") or 0.0),
        "mitigated_mean_risk": float(mit_map.get("average_class_risk") or 0.0),
        "baseline_uniqueness": float(orig_map.get("uniqueness") or 0.0),
        "mitigated_uniqueness": float(mit_map.get("uniqueness") or 0.0),
        "utility_loss": float(utility_loss),
    }


def evaluate_mitigation_linkage_tradeoff(
    orig_left: pd.DataFrame,
    orig_right: pd.DataFrame,
    mit_left: pd.DataFrame,
    mit_right: pd.DataFrame,
    truth: pd.DataFrame,
    left_dataset: str,
    right_dataset: str,
    qi_columns: Sequence[str],
    blocking_keys: Sequence[str],
    mitigation_name: str = "mitigation",
) -> MitigationTradeoffReport:
    """Evaluate privacy reduction vs linkage accuracy degradation under mitigation.

    Worst-case assumption: Attacker auxiliary knowledge undergoes the same
    mitigation transformation.
    """
    stats = evaluate_mitigation_on_dataset(
        orig_left, mit_left, qi_columns, mitigation_name
    )

    true_pairs = build_true_pairs(truth, left_dataset, right_dataset)
    b_pass = BlockingPass(columns=list(blocking_keys))

    # Linkage baseline
    cands_orig, _ = generate_candidate_pairs(orig_left, orig_right, [b_pass])
    specs = [
        AttributeComparatorSpec(attribute=col, method="exact", weight=1.0)
        for col in qi_columns
    ]
    preds_orig = similarity_linkage(
        orig_left,
        orig_right,
        cands_orig,
        specs,
        threshold=0.8,
        left_name=left_dataset,
        right_name=right_dataset,
    )
    res_orig = evaluate_linkage_predictions(
        preds_orig, true_pairs, total_true_pairs=len(true_pairs)
    )

    # Linkage mitigated
    cands_mit, _ = generate_candidate_pairs(mit_left, mit_right, [b_pass])
    preds_mit = similarity_linkage(
        mit_left,
        mit_right,
        cands_mit,
        specs,
        threshold=0.8,
        left_name=left_dataset,
        right_name=right_dataset,
    )
    res_mit = evaluate_linkage_predictions(
        preds_mit, true_pairs, total_true_pairs=len(true_pairs)
    )

    return MitigationTradeoffReport(
        mitigation_name=mitigation_name,
        baseline_max_risk=stats["baseline_max_risk"],
        mitigated_max_risk=stats["mitigated_max_risk"],
        baseline_mean_risk=stats["baseline_mean_risk"],
        mitigated_mean_risk=stats["mitigated_mean_risk"],
        baseline_uniqueness=stats["baseline_uniqueness"],
        mitigated_uniqueness=stats["mitigated_uniqueness"],
        baseline_linkage_f1=float(res_orig.f1_score or 0.0),
        mitigated_linkage_f1=float(res_mit.f1_score or 0.0),
        utility_loss=stats["utility_loss"],
    )
