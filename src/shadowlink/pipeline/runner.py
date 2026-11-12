"""End-to-end pipeline orchestrator connecting all SHADOWLINK modules."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from shadowlink.attacker.models import AttackerProfile
from shadowlink.attacker.simulator import simulate_attack
from shadowlink.common.exceptions import ShadowlinkError, ValidationError
from shadowlink.evaluator.ground_truth import build_true_pairs
from shadowlink.evaluator.metrics import (
    evaluate_blocking,
    evaluate_linkage_predictions,
    reidentification_success_rate,
)
from shadowlink.generator.generator import report_abc, wide_release
from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.fellegi_sunter import fellegi_sunter_linkage
from shadowlink.linkage.methods import deterministic_linkage, similarity_linkage
from shadowlink.linkage.models import AttributeComparatorSpec, FellegiSunterParams
from shadowlink.mitigation.pipeline import run_mitigation_experiment
from shadowlink.pipeline.models import PipelineConfig, PipelineReport
from shadowlink.profiler.profiler import profile_dataframe
from shadowlink.qi_analyser.candidates import find_candidate_qis
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.qi_analyser.overlap import find_shared_attributes
from shadowlink.risk.metrics import calculate_class_risk


class PipelineStageError(ShadowlinkError):
    """Raised when an end-to-end pipeline stage fails."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


def run_pipeline(
    config: PipelineConfig,
    out_dir: str | Path | None = None,
) -> PipelineReport:
    """Execute all 9 pipeline stages sequentially following Figure 1."""
    # -------------------------------------------------------------
    # Stage 1: Generate Synthetic Bundle
    # -------------------------------------------------------------
    stage1_name = "Stage 1: Generate Synthetic Bundle"
    try:
        if config.generator_preset == "wide_release":
            bundle = wide_release(
                seed=config.seed, population_size=config.population_size
            )
        else:
            bundle = report_abc(
                seed=config.seed,
                population_size=config.population_size,
                shared_fraction=config.shared_fraction,
                typo_rate=config.typo_rate,
                missing_rate=config.missing_rate,
            )

        stage1_summary = {
            "preset": config.generator_preset,
            "population_size": config.population_size,
            "shared_fraction": config.shared_fraction,
            "record_counts": {
                name: len(df) for name, df in bundle.datasets.items()
            },
            "total_typos": bundle.manifest.get("total_typos_injected", 0),
            "total_missing": bundle.manifest.get("total_missing_injected", 0),
        }
    except Exception as exc:
        raise PipelineStageError(stage1_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 2: Profile Every Dataset
    # -------------------------------------------------------------
    stage2_name = "Stage 2: Profile Every Dataset"
    try:
        profiles: dict[str, Any] = {}
        profile_objects = []
        for ds_name, df in sorted(bundle.datasets.items()):
            prof = profile_dataframe(df, dataset_name=ds_name)
            profile_objects.append(prof)
            col_list: list[dict[str, Any]] = []
            for c in prof.columns:
                col_list.append(
                    {
                        "name": c.name,
                        "kind": c.kind,
                        "distinct_count": c.distinct_count,
                        "missing_rate": c.missing_rate,
                        "uniqueness_ratio": c.uniqueness_ratio,
                    }
                )
            profiles[ds_name] = {
                "rows": prof.row_count,
                "columns": prof.column_count,
                "column_details": col_list,
            }
    except Exception as exc:
        raise PipelineStageError(stage2_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 3: Shared Attributes + Candidate QIs
    # -------------------------------------------------------------
    stage3_name = "Stage 3: Shared Attributes & Candidate QIs"
    try:
        shared_map = find_shared_attributes(profile_objects)
        detected_qis = find_candidate_qis(profile_objects)

        stage3_summary = {
            "shared_attributes": sorted(list(shared_map.keys())),
            "candidate_qis": sorted(
                list({c.column_name for c in detected_qis})
            ),
        }
    except Exception as exc:
        raise PipelineStageError(stage3_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 4: Equivalence Classes + Class-Based Risk
    # -------------------------------------------------------------
    stage4_name = "Stage 4: Equivalence Classes & Class Risk"
    try:
        if config.target_dataset not in bundle.datasets:
            raise ValidationError(
                f"Target dataset '{config.target_dataset}' not in bundle."
            )
        target_df = bundle.datasets[config.target_dataset]
        eq = build_equivalence_classes(target_df, qi_columns=config.qi_columns)
        risk_rep = calculate_class_risk(eq)
        r_map = {m.name: m.value for m in risk_rep.metrics}

        stage4_summary = {
            "target_dataset": config.target_dataset,
            "qi_columns": config.qi_columns,
            "num_classes": eq.num_classes,
            "k": eq.k,
            "uniqueness": float(r_map.get("uniqueness") or 0.0),
            "max_class_risk": float(r_map.get("max_class_risk") or 0.0),
            "average_class_risk": float(
                r_map.get("average_class_risk") or 0.0
            ),
            "discernibility_metric": int(
                r_map.get("discernibility_metric") or 0
            ),
        }
    except Exception as exc:
        raise PipelineStageError(stage4_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 5: Attacker Narrowing Curve + Candidate Risk
    # -------------------------------------------------------------
    stage5_name = "Stage 5: Attacker Narrowing Curve"
    try:
        profile = AttackerProfile(
            name="pipeline_attacker", steps=config.attacker_steps
        )
        n_targets = min(config.attacker_targets, len(target_df))
        atk_res = simulate_attack(
            target_df, profile, n_targets=n_targets, seed=config.seed
        )

        step_rows: list[dict[str, Any]] = []
        for s in atk_res.step_reports:
            step_rows.append(
                {
                    "step": s.step,
                    "attributes": "+".join(s.attributes),
                    "mean_candidates": s.mean_candidates,
                    "mean_risk": s.mean_risk,
                    "unique_fraction": s.unique_fraction,
                    "expected_success": s.expected_success_rate,
                }
            )

        stage5_summary = {"steps": step_rows}
    except Exception as exc:
        raise PipelineStageError(stage5_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 6: Linkage Engine (Deterministic, Similarity, Fellegi-Sunter)
    # (Note: Stage 6 NEVER touches ground truth!)
    # -------------------------------------------------------------
    stage6_name = "Stage 6: Record Linkage Engine"
    try:
        left_df = bundle.datasets[config.linkage_left]
        right_df = bundle.datasets[config.linkage_right]

        b_pass = BlockingPass(columns=config.linkage_blocking_keys)
        cands, b_report = generate_candidate_pairs(left_df, right_df, [b_pass])

        # 1. Deterministic Linkage
        det_preds = deterministic_linkage(
            left_df,
            right_df,
            cands,
            attributes=config.linkage_attributes,
            left_name=config.linkage_left,
            right_name=config.linkage_right,
        )

        # 2. Similarity Linkage
        specs = [
            AttributeComparatorSpec(
                attribute=a, method="jaro_winkler", weight=1.0
            )
            for a in config.linkage_attributes
        ]
        sim_preds = similarity_linkage(
            left_df,
            right_df,
            cands,
            specs,
            threshold=config.linkage_threshold,
            left_name=config.linkage_left,
            right_name=config.linkage_right,
        )

        # 3. Fellegi-Sunter Linkage (prior-based, uncalibrated)
        fs_params = FellegiSunterParams(
            m_probabilities={a: 0.90 for a in config.linkage_attributes},
            u_probabilities={a: 0.10 for a in config.linkage_attributes},
        )
        fs_preds = fellegi_sunter_linkage(
            left_df,
            right_df,
            cands,
            specs,
            params=fs_params,
            lower_threshold=-1.0,
            upper_threshold=1.0,
            left_name=config.linkage_left,
            right_name=config.linkage_right,
        )

        stage6_summary = {
            "left_dataset": config.linkage_left,
            "right_dataset": config.linkage_right,
            "blocking_keys": config.linkage_blocking_keys,
            "candidate_pairs_count": len(cands),
            "reduction_ratio": b_report.reduction_ratio,
            "det_matches": int((det_preds["decision"] == "match").sum()),
            "sim_matches": int((sim_preds["decision"] == "match").sum()),
            "fs_matches": int((fs_preds["decision"] == "match").sum()),
        }
    except Exception as exc:
        raise PipelineStageError(stage6_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 7: Privacy Mitigation & Re-running Stages 4-6
    # -------------------------------------------------------------
    stage7_name = "Stage 7: Privacy Mitigation"
    try:
        _ = run_mitigation_experiment(
            target_df,
            specs=config.mitigation_transformations,
            qi_columns=config.qi_columns,
        )
        # Apply sequential transformations to get the transformed dataframe
        cur_df = target_df.copy(deep=True)
        from shadowlink.mitigation.generalization import generalize_age
        from shadowlink.mitigation.suppression import suppress_rare_values
        from shadowlink.mitigation.temporal import coarsen_timestamp

        for tx in config.mitigation_transformations:
            if tx.kind == "generalize_age":
                cur_df = generalize_age(cur_df, **tx.parameters).df
            elif tx.kind == "coarsen_timestamp":
                cur_df = coarsen_timestamp(cur_df, **tx.parameters).df
            elif tx.kind == "suppress_rare_values":
                cur_df = suppress_rare_values(cur_df, **tx.parameters).df

        mitigated_target_df = cur_df

        # Re-run Stage 4 on mitigated dataset
        eq_mit = build_equivalence_classes(
            mitigated_target_df, qi_columns=config.qi_columns
        )
        risk_mit = calculate_class_risk(eq_mit)
        r_map_mit = {m.name: m.value for m in risk_mit.metrics}

        # Re-run Stage 5 on mitigated dataset
        atk_mit = simulate_attack(
            mitigated_target_df, profile, n_targets=n_targets, seed=config.seed
        )

        # Re-run Stage 6 on mitigated data
        mit_left = (
            mitigated_target_df
            if config.target_dataset == config.linkage_left
            else left_df
        )
        mit_right = (
            mitigated_target_df
            if config.target_dataset == config.linkage_right
            else right_df
        )

        cands_mit, _ = generate_candidate_pairs(
            mit_left, mit_right, [b_pass]
        )
        det_preds_mit = deterministic_linkage(
            mit_left,
            mit_right,
            cands_mit,
            attributes=config.linkage_attributes,
            left_name=config.linkage_left,
            right_name=config.linkage_right,
        )
        sim_preds_mit = similarity_linkage(
            mit_left,
            mit_right,
            cands_mit,
            specs,
            threshold=config.linkage_threshold,
            left_name=config.linkage_left,
            right_name=config.linkage_right,
        )
        fs_preds_mit = fellegi_sunter_linkage(
            mit_left,
            mit_right,
            cands_mit,
            specs,
            params=fs_params,
            lower_threshold=-1.0,
            upper_threshold=1.0,
            left_name=config.linkage_left,
            right_name=config.linkage_right,
        )

        # Calculate cell utility loss
        common_cols = [
            c
            for c in target_df.columns
            if c in mitigated_target_df.columns and c != "record_id"
        ]
        diff_cells = sum(
            int((target_df[c].astype(str) != mitigated_target_df[c].astype(str)).sum())
            for c in common_cols
        )
        tot_cells = len(target_df) * max(1, len(common_cols))
        u_loss = diff_cells / tot_cells if tot_cells > 0 else 0.0

        stage7_summary = {
            "applied_transformations": len(config.mitigation_transformations),
            "utility_loss": float(u_loss),
            "baseline_average_risk": float(r_map.get("average_class_risk") or 0.0),
            "mitigated_average_risk": float(r_map_mit.get("average_class_risk") or 0.0),
            "baseline_k": eq.k,
            "mitigated_k": eq_mit.k,
            "mitigated_attacker_final_risk": atk_mit.step_reports[-1].mean_risk,
        }
    except Exception as exc:
        raise PipelineStageError(stage7_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 8: Evaluation (ONLY stage that reads ground truth)
    # -------------------------------------------------------------
    stage8_name = "Stage 8: Evaluation"
    try:
        truth = bundle.ground_truth
        true_pairs = build_true_pairs(
            truth, config.linkage_left, config.linkage_right
        )
        tot_true = len(true_pairs)

        # Evaluate Stage 6 predictions
        ev_det = evaluate_linkage_predictions(
            det_preds, true_pairs, total_true_pairs=tot_true
        )
        ev_sim = evaluate_linkage_predictions(
            sim_preds, true_pairs, total_true_pairs=tot_true
        )
        ev_fs = evaluate_linkage_predictions(
            fs_preds, true_pairs, total_true_pairs=tot_true
        )

        # Evaluate Stage 7 mitigated predictions
        ev_det_m = evaluate_linkage_predictions(
            det_preds_mit, true_pairs, total_true_pairs=tot_true
        )
        ev_sim_m = evaluate_linkage_predictions(
            sim_preds_mit, true_pairs, total_true_pairs=tot_true
        )
        ev_fs_m = evaluate_linkage_predictions(
            fs_preds_mit, true_pairs, total_true_pairs=tot_true
        )

        # Blocking evaluation
        b_eval = evaluate_blocking(
            cands, true_pairs, naive_comparisons=len(left_df) * len(right_df)
        )

        # Re-identification success rate
        reid_eval = reidentification_success_rate(
            sim_preds,
            truth,
            left_dataset=config.linkage_left,
            right_dataset=config.linkage_right,
        )

        stage8_summary = {
            "methods": {
                "Deterministic": {
                    "orig_precision": float(ev_det.precision or 0.0),
                    "orig_recall": float(ev_det.recall or 0.0),
                    "orig_f1": float(ev_det.f1_score or 0.0),
                    "mit_f1": float(ev_det_m.f1_score or 0.0),
                },
                "Similarity (Jaro-Winkler)": {
                    "orig_precision": float(ev_sim.precision or 0.0),
                    "orig_recall": float(ev_sim.recall or 0.0),
                    "orig_f1": float(ev_sim.f1_score or 0.0),
                    "mit_f1": float(ev_sim_m.f1_score or 0.0),
                },
                "Fellegi-Sunter": {
                    "orig_precision": float(ev_fs.precision or 0.0),
                    "orig_recall": float(ev_fs.recall or 0.0),
                    "orig_f1": float(ev_fs.f1_score or 0.0),
                    "mit_f1": float(ev_fs_m.f1_score or 0.0),
                },
            },
            "pairs_completeness": b_eval.pairs_completeness,
            "tie_adjusted_reid_success": reid_eval.tie_adjusted_success_rate,
            "deterministic_reid_success": reid_eval.deterministic_success_rate,
        }
    except Exception as exc:
        raise PipelineStageError(stage8_name, str(exc)) from exc

    # -------------------------------------------------------------
    # Stage 9: Write One Report (report.json + report.md)
    # -------------------------------------------------------------
    stage9_name = "Stage 9: Report Writer"
    try:
        metadata = {
            "seed": config.seed,
            "population_size": config.population_size,
            "python_version": platform.python_version(),
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
        }
        report = PipelineReport(
            metadata=metadata,
            stage1_generation=stage1_summary,
            stage2_profiles=profiles,
            stage3_shared_and_qis=stage3_summary,
            stage4_risk=stage4_summary,
            stage5_attacker=stage5_summary,
            stage6_linkage=stage6_summary,
            stage7_mitigation=stage7_summary,
            stage8_evaluation=stage8_summary,
        )

        if out_dir is not None:
            out_p = Path(out_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            (out_p / "report.json").write_text(report.to_json(), encoding="utf-8")
            (out_p / "report.md").write_text(report.to_markdown(), encoding="utf-8")

        return report
    except Exception as exc:
        raise PipelineStageError(stage9_name, str(exc)) from exc
