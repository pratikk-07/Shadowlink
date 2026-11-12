"""Benchmark experiment runners producing Tables 5, 6, and 7."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from shadowlink.attacker.models import AttackerProfile
from shadowlink.attacker.simulator import simulate_attack
from shadowlink.evaluator.calibration import estimate_m_u_from_ground_truth
from shadowlink.evaluator.ground_truth import build_true_pairs
from shadowlink.evaluator.metrics import (
    evaluate_blocking,
    evaluate_linkage_predictions,
)
from shadowlink.evaluator.tables import (
    format_csv_with_header,
    format_markdown_table,
    generate_experiment_metadata,
)
from shadowlink.generator.generator import report_abc, wide_release
from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.fellegi_sunter import fellegi_sunter_linkage
from shadowlink.linkage.methods import deterministic_linkage, similarity_linkage
from shadowlink.linkage.models import AttributeComparatorSpec
from shadowlink.mitigation.generalization import generalize_age
from shadowlink.mitigation.suppression import suppress_rare_values
from shadowlink.mitigation.temporal import coarsen_timestamp
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.metrics import calculate_class_risk


def run_table5_experiment(
    n: int = 500,
    seed: int = 42,
    targets_count: int | None = 100,
) -> tuple[pd.DataFrame, str, str]:
    """Execute Table 5: Attacker progression with progressive attribute disclosure.

    Evaluates re-identification risk on wide_release dataset W across four steps:
    1. (age, city)
    2. (age, city, course)
    3. (age, city, course, location)
    4. (age, city, course, location, timestamp)

    Returns:
        (DataFrame, markdown_table, csv_with_header)
    """
    bundle = wide_release(seed=seed, population_size=n)
    df_w = bundle.datasets["W"]

    profile = AttackerProfile.strong()
    n_targets = targets_count if targets_count is not None else len(df_w)
    attack_result = simulate_attack(
        df_w, profile=profile, seed=seed, n_targets=n_targets
    )

    labels = ["Age, City", "+Course", "+Location", "+Timestamp"]
    rows: list[dict[str, Any]] = []

    for idx, report in enumerate(attack_result.step_reports):
        step_lbl = f"Step {report.step}"
        attr_lbl = labels[idx] if idx < len(labels) else "+".join(report.attributes)
        rows.append(
            {
                "Step": step_lbl,
                "Attributes Disclosed": attr_lbl,
                "Mean Candidate Size": report.mean_candidates,
                "Mean Candidate Risk": report.mean_risk,
                "Proportion Unique (c=1)": report.unique_fraction,
                "Expected Success Rate": report.expected_success_rate,
            }
        )

    res_df = pd.DataFrame(rows)
    meta = generate_experiment_metadata(
        "Table 5 - Attacker Progression",
        n=n,
        seed=seed,
        extra_metadata={"Evaluated Targets": n_targets},
    )
    md = format_markdown_table(res_df, "Table 5: Progressive Attacker Simulator")
    csv_str = format_csv_with_header(res_df, meta)
    return res_df, md, csv_str


def run_table6_experiment(
    n: int = 500,
    shared_fraction: float = 0.5,
    seed: int = 42,
) -> tuple[pd.DataFrame, str, str]:
    """Execute Table 6: Linkage methods comparison on report_abc A-B.

    Compares Deterministic, Similarity (Jaro-Winkler), and Fellegi-Sunter methods.

    Returns:
        (DataFrame, markdown_table, csv_with_header)
    """
    bundle = report_abc(
        seed=seed, population_size=n, shared_fraction=shared_fraction
    )
    df_a = bundle.datasets["A"]
    df_b = bundle.datasets["B"]
    truth = bundle.ground_truth

    true_pairs = build_true_pairs(truth, "A", "B")
    total_true = len(true_pairs)

    # Common blocking on city
    b_pass = BlockingPass(columns=["city"])
    naive_comps = len(df_a) * len(df_b)
    cands, b_report = generate_candidate_pairs(df_a, df_b, [b_pass])
    b_eval = evaluate_blocking(cands, true_pairs, naive_comparisons=naive_comps)

    # Fellegi-Sunter calibration
    calib_params = estimate_m_u_from_ground_truth(
        left_df=df_a,
        right_df=df_b,
        candidate_pairs=cands,
        truth=truth,
        left_dataset="A",
        right_dataset="B",
        attributes=["age", "city"],
        smoothing=1.0,
    )

    rows: list[dict[str, Any]] = []

    # 1. Deterministic
    t0 = time.perf_counter()
    det_preds = deterministic_linkage(
        df_a,
        df_b,
        cands,
        attributes=["age", "city"],
        left_name="A",
        right_name="B",
    )
    t_det = time.perf_counter() - t0
    det_eval = evaluate_linkage_predictions(
        det_preds, true_pairs, total_true_pairs=total_true
    )
    rows.append(
        {
            "Method": "Deterministic (Exact)",
            "Candidates": len(cands),
            "Matches Predicted": len(det_preds[det_preds["decision"] == "match"]),
            "True Positives": det_eval.true_positives,
            "Precision": float(det_eval.precision or 0.0),
            "Recall": float(det_eval.recall or 0.0),
            "F1 Score": float(det_eval.f1_score or 0.0),
            "Reduction Ratio": b_eval.reduction_ratio,
            "Runtime (s)": t_det,
        }
    )

    # 2. Similarity (Jaro-Winkler on city, exact on age)
    specs = [
        AttributeComparatorSpec(
            attribute="city", method="jaro_winkler", weight=1.0
        ),
        AttributeComparatorSpec(attribute="age", method="exact", weight=1.0),
    ]
    t0 = time.perf_counter()
    sim_preds = similarity_linkage(
        df_a,
        df_b,
        cands,
        specs,
        threshold=0.85,
        left_name="A",
        right_name="B",
    )
    t_sim = time.perf_counter() - t0
    sim_eval = evaluate_linkage_predictions(
        sim_preds, true_pairs, total_true_pairs=total_true
    )
    rows.append(
        {
            "Method": "Similarity (Jaro-Winkler)",
            "Candidates": len(cands),
            "Matches Predicted": len(sim_preds[sim_preds["decision"] == "match"]),
            "True Positives": sim_eval.true_positives,
            "Precision": float(sim_eval.precision or 0.0),
            "Recall": float(sim_eval.recall or 0.0),
            "F1 Score": float(sim_eval.f1_score or 0.0),
            "Reduction Ratio": b_eval.reduction_ratio,
            "Runtime (s)": t_sim,
        }
    )

    # 3. Fellegi-Sunter
    t0 = time.perf_counter()
    fs_preds = fellegi_sunter_linkage(
        df_a,
        df_b,
        cands,
        specs,
        params=calib_params,
        lower_threshold=-1.0,
        upper_threshold=1.0,
        left_name="A",
        right_name="B",
    )
    t_fs = time.perf_counter() - t0
    fs_eval = evaluate_linkage_predictions(
        fs_preds, true_pairs, total_true_pairs=total_true
    )
    rows.append(
        {
            "Method": "Fellegi-Sunter",
            "Candidates": len(cands),
            "Matches Predicted": len(fs_preds[fs_preds["decision"] == "match"]),
            "True Positives": fs_eval.true_positives,
            "Precision": float(fs_eval.precision or 0.0),
            "Recall": float(fs_eval.recall or 0.0),
            "F1 Score": float(fs_eval.f1_score or 0.0),
            "Reduction Ratio": b_eval.reduction_ratio,
            "Runtime (s)": t_fs,
        }
    )

    res_df = pd.DataFrame(rows)
    meta = generate_experiment_metadata(
        "Table 6 - Linkage Methods Comparison",
        n=n,
        seed=seed,
        shared_fraction=shared_fraction,
    )
    md = format_markdown_table(res_df, "Table 6: Linkage Methods Benchmark")
    csv_str = format_csv_with_header(res_df, meta)
    return res_df, md, csv_str


def run_table7_experiment(
    n: int = 500,
    shared_fraction: float = 0.5,
    seed: int = 42,
) -> tuple[pd.DataFrame, str, str]:
    """Execute Table 7: Mitigation tradeoffs on A-B linkage & class risk.

    Evaluates:
    1. Baseline (Unmitigated)
    2. Age Generalisation (5-year bins)
    3. Timestamp Coarsening (day level on B)
    4. Rare City Suppression (freq < 5)
    5. Combined Mitigation

    Returns:
        (DataFrame, markdown_table, csv_with_header)
    """
    bundle = report_abc(
        seed=seed,
        population_size=n,
        shared_fraction=shared_fraction,
        typo_rate=0.0,
        missing_rate=0.0,
    )
    df_a = bundle.datasets["A"]
    df_b = bundle.datasets["B"]
    truth = bundle.ground_truth
    true_pairs = build_true_pairs(truth, "A", "B")
    total_true = len(true_pairs)

    specs = [
        AttributeComparatorSpec(attribute="city", method="exact", weight=1.0),
        AttributeComparatorSpec(attribute="age", method="exact", weight=1.0),
    ]

    def _eval_condition(
        cond_name: str,
        cur_a: pd.DataFrame,
        cur_b: pd.DataFrame,
        qi_cols: list[str],
    ) -> dict[str, Any]:
        # Privacy risk on A
        eq = build_equivalence_classes(cur_a, qi_columns=qi_cols)
        c_risk = calculate_class_risk(eq)
        r_map = {m.name: m.value for m in c_risk.metrics}

        # Linkage A-B
        b_pass = (
            BlockingPass(columns=["city"])
            if "city" in cur_a.columns and "city" in cur_b.columns
            else BlockingPass(columns=["age"])
        )
        cands, _ = generate_candidate_pairs(cur_a, cur_b, [b_pass])
        preds = similarity_linkage(
            cur_a,
            cur_b,
            cands,
            specs,
            threshold=0.8,
            left_name="A",
            right_name="B",
        )
        l_eval = evaluate_linkage_predictions(
            preds, true_pairs, total_true_pairs=total_true
        )

        # Utility loss (fraction of altered cells in A + B vs original)
        diff_a = int((df_a != cur_a).sum().sum())
        diff_b = int((df_b != cur_b).sum().sum())
        total_cells = df_a.size + df_b.size
        u_loss = (diff_a + diff_b) / total_cells if total_cells > 0 else 0.0

        return {
            "Condition": cond_name,
            "Max Class Risk": float(r_map.get("max_class_risk") or 0.0),
            "Mean Class Risk": float(r_map.get("average_class_risk") or 0.0),
            "Uniqueness (k=1)": float(r_map.get("uniqueness") or 0.0),
            "Linkage Precision": float(l_eval.precision or 0.0),
            "Linkage Recall": float(l_eval.recall or 0.0),
            "Linkage F1": float(l_eval.f1_score or 0.0),
            "Utility Loss": float(u_loss),
        }

    rows: list[dict[str, Any]] = []

    # 1. Baseline
    rows.append(
        _eval_condition("1. Baseline (Unmitigated)", df_a, df_b, ["age", "city"])
    )

    # 2. Age Generalisation (bin_width=5)
    a_gen = generalize_age(df_a, "age", bin_width=5).df
    b_gen = generalize_age(df_b, "age", bin_width=5).df
    rows.append(
        _eval_condition("2. Age Generalisation", a_gen, b_gen, ["age", "city"])
    )

    # 3. Timestamp Coarsening (day on B)
    b_ts = coarsen_timestamp(df_b, "timestamp", level="day").df
    rows.append(
        _eval_condition("3. Timestamp Coarsening", df_a, b_ts, ["age", "city"])
    )

    # 4. Rare City Suppression (freq < 5)
    a_sup = suppress_rare_values(df_a, "city", minimum_frequency=5).df
    b_sup = suppress_rare_values(df_b, "city", minimum_frequency=5).df
    rows.append(
        _eval_condition("4. Rare City Suppression", a_sup, b_sup, ["age", "city"])
    )

    # 5. Combined
    a_comb = suppress_rare_values(a_gen, "city", minimum_frequency=5).df
    b_comb = suppress_rare_values(b_gen, "city", minimum_frequency=5).df
    b_comb = coarsen_timestamp(b_comb, "timestamp", level="day").df
    rows.append(
        _eval_condition("5. Combined Mitigation", a_comb, b_comb, ["age", "city"])
    )

    res_df = pd.DataFrame(rows)
    meta = generate_experiment_metadata(
        "Table 7 - Mitigation Tradeoffs",
        n=n,
        seed=seed,
        shared_fraction=shared_fraction,
    )
    md = format_markdown_table(res_df, "Table 7: Mitigation Privacy-Utility Tradeoffs")
    csv_str = format_csv_with_header(res_df, meta)
    return res_df, md, csv_str
