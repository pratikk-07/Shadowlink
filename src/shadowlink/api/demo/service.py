"""In-memory service layer orchestrating platform modules for the demo dashboard."""

from __future__ import annotations

import collections
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from shadowlink.api.demo.models import (
    AttackSimulationRequest,
    CreateRunRequest,
    LinkageRequest,
    MitigationRequest,
    QIAnalysisRequest,
    RunSummaryResponse,
)
from shadowlink.attacker.models import AttackerProfile
from shadowlink.attacker.simulator import simulate_attack
from shadowlink.common.exceptions import ShadowlinkError, ValidationError
from shadowlink.evaluator.calibration import estimate_m_u_from_ground_truth
from shadowlink.evaluator.experiments import (
    run_table5_experiment,
    run_table6_experiment,
    run_table7_experiment,
)
from shadowlink.evaluator.ground_truth import build_true_pairs
from shadowlink.evaluator.metrics import (
    evaluate_blocking,
    evaluate_linkage_predictions,
    reidentification_success_rate,
)
from shadowlink.generator.generator import (
    GeneratedBundle,
    report_abc,
    wide_release,
)
from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.fellegi_sunter import fellegi_sunter_linkage
from shadowlink.linkage.methods import deterministic_linkage, similarity_linkage
from shadowlink.linkage.models import AttributeComparatorSpec
from shadowlink.mitigation.generalization import generalize_age
from shadowlink.mitigation.models import TransformationSpec
from shadowlink.mitigation.pipeline import run_mitigation_experiment
from shadowlink.mitigation.suppression import suppress_rare_values
from shadowlink.mitigation.temporal import coarsen_timestamp
from shadowlink.pipeline.models import PipelineConfig
from shadowlink.pipeline.runner import run_pipeline as run_pipeline_orchestrator
from shadowlink.profiler.models import DatasetProfile
from shadowlink.profiler.profiler import profile_dataframe
from shadowlink.qi_analyser.candidates import find_candidate_qis
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.qi_analyser.overlap import find_shared_attributes
from shadowlink.risk.metrics import calculate_class_risk


@dataclass
class RunState:
    """In-memory state of an active benchmark run."""

    run_id: str
    preset: str
    population_size: int
    shared_fraction: float
    typo_rate: float
    missing_rate: float
    seed: int
    bundle: GeneratedBundle
    profiles: dict[str, DatasetProfile]
    stage_status: dict[str, str] = field(
        default_factory=lambda: {
            "1. Generation": "done",
            "2. Profiling": "done",
            "3. QI Analysis": "not run",
            "4. Risk Engine": "not run",
            "5. Attacker Simulator": "not run",
            "6. Linkage Engine": "not run",
            "7. Mitigation": "not run",
            "8. Evaluator": "not run",
            "9. Report": "not run",
        }
    )


class DemoService:
    """Service managing demo runs and executing platform actions."""

    MAX_RUNS = 5

    def __init__(self) -> None:
        self._runs: collections.OrderedDict[str, RunState] = (
            collections.OrderedDict()
        )

    def _get_run(self, run_id: str) -> RunState:
        if run_id not in self._runs:
            raise ShadowlinkError(f"Run '{run_id}' not found.")
        return self._runs[run_id]

    def has_run(self, run_id: str) -> bool:
        """Check whether a run exists and has not been evicted."""
        return run_id in self._runs

    def create_run(self, req: CreateRunRequest) -> RunSummaryResponse:
        """Generate a new synthetic benchmark bundle and profile every dataset."""
        if req.preset == "wide_release":
            bundle = wide_release(
                seed=req.seed, population_size=req.population_size
            )
        else:
            bundle = report_abc(
                seed=req.seed,
                population_size=req.population_size,
                shared_fraction=req.shared_fraction,
                typo_rate=req.typo_rate,
                missing_rate=req.missing_rate,
            )

        profiles: dict[str, DatasetProfile] = {}
        dataset_counts: dict[str, int] = {}
        dataset_previews: dict[str, list[dict[str, Any]]] = {}
        dataset_profile_summaries: dict[str, Any] = {}

        for name, df in sorted(bundle.datasets.items()):
            dataset_counts[name] = len(df)
            prof = profile_dataframe(df, dataset_name=name)
            profiles[name] = prof

            # First 10 rows preview without ground truth columns
            preview_df = df.head(10).copy()
            for forbidden_col in ["entity_id", "ground_truth", "true_id"]:
                if forbidden_col in preview_df.columns:
                    preview_df = preview_df.drop(columns=[forbidden_col])

            preview_records: list[dict[str, Any]] = []
            for _, row in preview_df.iterrows():
                row_dict: dict[str, Any] = {}
                for col_name, val in row.items():
                    if pd.isna(val):
                        row_dict[str(col_name)] = None
                    else:
                        row_dict[str(col_name)] = val
                preview_records.append(row_dict)
            dataset_previews[name] = preview_records

            # Profile summary
            col_summaries = []
            for c in prof.columns:
                col_summaries.append(
                    {
                        "name": c.name,
                        "kind": c.kind,
                        "distinct_count": c.distinct_count,
                        "missing_rate": c.missing_rate,
                        "uniqueness_ratio": c.uniqueness_ratio,
                    }
                )
            dataset_profile_summaries[name] = {
                "rows": prof.row_count,
                "columns": prof.column_count,
                "column_details": col_summaries,
            }

        run_id = f"run_{req.seed}_{uuid.uuid4().hex[:8]}"

        # Evict oldest run if capacity reached
        if len(self._runs) >= self.MAX_RUNS:
            self._runs.popitem(last=False)

        state = RunState(
            run_id=run_id,
            preset=req.preset,
            population_size=req.population_size,
            shared_fraction=req.shared_fraction,
            typo_rate=req.typo_rate,
            missing_rate=req.missing_rate,
            seed=req.seed,
            bundle=bundle,
            profiles=profiles,
        )
        self._runs[run_id] = state

        return RunSummaryResponse(
            run_id=run_id,
            preset=req.preset,
            population_size=req.population_size,
            shared_fraction=req.shared_fraction,
            seed=req.seed,
            dataset_counts=dataset_counts,
            dataset_previews=dataset_previews,
            dataset_profiles=dataset_profile_summaries,
            stage_status=state.stage_status,
        )

    def get_profile(self, run_id: str) -> dict[str, Any]:
        """Retrieve detailed statistical profiles for all datasets in run."""
        state = self._get_run(run_id)
        profiles_dict: dict[str, Any] = {}
        for name, prof in state.profiles.items():
            profiles_dict[name] = {
                "rows": prof.row_count,
                "columns": prof.column_count,
                "duplicate_rows": prof.duplicate_row_count,
                "column_details": [
                    {
                        "name": c.name,
                        "kind": c.kind,
                        "distinct_count": c.distinct_count,
                        "missing_rate": c.missing_rate,
                        "uniqueness_ratio": c.uniqueness_ratio,
                    }
                    for c in prof.columns
                ],
            }
        return {"run_id": run_id, "profiles": profiles_dict}

    def analyze_qi(
        self, run_id: str, req: QIAnalysisRequest
    ) -> dict[str, Any]:
        """Compute candidate QIs, shared attributes, and equivalence class risk."""
        state = self._get_run(run_id)
        if req.dataset_name not in state.bundle.datasets:
            raise ValidationError(
                f"Dataset '{req.dataset_name}' not found in run."
            )

        df = state.bundle.datasets[req.dataset_name]
        profile_list = list(state.profiles.values())

        # 1. Candidate QIs & Shared Attributes
        candidate_qis = find_candidate_qis(profile_list)
        shared_map = find_shared_attributes(profile_list)

        # 2. Equivalence Classes on chosen QIs
        eq = build_equivalence_classes(df, qi_columns=req.qi_columns)
        risk_rep = calculate_class_risk(eq)

        # Class sizes histogram bins (1, 2-4, 5-9, 10+)
        bins = {"1 (Unique)": 0, "2-4": 0, "5-9": 0, "10+": 0}
        for sz in eq.class_sizes:
            if sz == 1:
                bins["1 (Unique)"] += 1
            elif sz <= 4:
                bins["2-4"] += 1
            elif sz <= 9:
                bins["5-9"] += 1
            else:
                bins["10+"] += 1

        risk_metrics: list[dict[str, Any]] = []
        for m in risk_rep.metrics:
            risk_metrics.append(
                {
                    "name": m.name,
                    "value": m.value,
                    "denominator": m.denominator,
                    "formula": m.formula,
                    "assumption": m.assumption,
                    "explanation": m.explanation,
                }
            )

        state.stage_status["3. QI Analysis"] = "done"
        state.stage_status["4. Risk Engine"] = "done"

        return {
            "run_id": run_id,
            "dataset_name": req.dataset_name,
            "qi_columns": req.qi_columns,
            "k_anonymity": eq.k,
            "singleton_proportion": eq.singleton_record_proportion,
            "max_risk": (
                float(1.0 / eq.k) if (eq.k is not None and eq.k > 0) else None
            ),
            "average_risk": (
                float(eq.num_classes / eq.records_analysed)
                if eq.records_analysed > 0
                else 0.0
            ),
            "candidate_qis": [
                {
                    "column_name": c.column_name,
                    "dataset_name": c.dataset_name,
                    "reasons": c.reasons,
                }
                for c in candidate_qis
                if c.dataset_name == req.dataset_name
            ],
            "shared_attributes": sorted(list(shared_map.keys())),
            "equivalence_classes": {
                "num_classes": eq.num_classes,
                "k": eq.k,
                "singleton_class_count": eq.singleton_class_count,
                "singleton_record_proportion": eq.singleton_record_proportion,
                "class_size_distribution": bins,
                "class_sizes": list(eq.class_sizes),
            },
            "risk_metrics": risk_metrics,
            "stage_status": state.stage_status,
        }

    def simulate_attack(
        self, run_id: str, req: AttackSimulationRequest
    ) -> dict[str, Any]:
        """Simulate progressive disclosure re-identification narrowing curve."""
        state = self._get_run(run_id)
        if req.dataset_name not in state.bundle.datasets:
            raise ValidationError(
                f"Dataset '{req.dataset_name}' not found in run."
            )

        df = state.bundle.datasets[req.dataset_name]
        if not req.steps:
            raise ValidationError("At least one attack step must be provided.")

        valid_cols = set(df.columns)
        for idx, step in enumerate(req.steps, 1):
            if not step:
                raise ValidationError(f"Attack step {idx} cannot be empty.")
            for col in step:
                if col in (
                    "entity_id",
                    "ground_truth",
                    "true_id",
                    "identity_key",
                ):
                    raise ValidationError(
                        f"Forbidden column in attack step: '{col}'."
                    )
                if col not in valid_cols:
                    raise ValidationError(
                        f"Unknown column '{col}' in attack step {idx}. "
                        f"Available columns in dataset '{req.dataset_name}': "
                        f"{sorted(valid_cols)}"
                    )

        steps = [tuple(step) for step in req.steps]
        profile = AttackerProfile(name="demo_attack", steps=steps)
        n_targets = min(req.n_targets, len(df))

        result = simulate_attack(
            df, profile, n_targets=n_targets, seed=req.seed
        )

        step_reports: list[dict[str, Any]] = []
        for s in result.step_reports:
            step_reports.append(
                {
                    "step": s.step,
                    "attributes": "+".join(s.attributes),
                    "mean_candidates": s.mean_candidates,
                    "median_candidates": s.median_candidates,
                    "min_candidates": s.min_candidates,
                    "max_candidates": s.max_candidates,
                    "mean_risk": s.mean_risk,
                    "mean_reduction": s.mean_reduction,
                    "unique_fraction": s.unique_fraction,
                    "expected_success_rate": s.expected_success_rate,
                }
            )

        state.stage_status["5. Attacker Simulator"] = "done"

        return {
            "run_id": run_id,
            "dataset_name": req.dataset_name,
            "n_targets": n_targets,
            "seed": req.seed,
            "steps": step_reports,
            "narrowing_curve": step_reports,
            "stage_status": state.stage_status,
        }

    def link_datasets(
        self, run_id: str, req: LinkageRequest
    ) -> dict[str, Any]:
        """Perform candidate pair blocking and comparative record linkage."""
        state = self._get_run(run_id)
        if req.left_dataset not in state.bundle.datasets:
            raise ValidationError(
                f"Dataset '{req.left_dataset}' not found in run."
            )
        if req.right_dataset not in state.bundle.datasets:
            raise ValidationError(
                f"Dataset '{req.right_dataset}' not found in run."
            )

        left_df = state.bundle.datasets[req.left_dataset]
        right_df = state.bundle.datasets[req.right_dataset]

        # Blocking
        b_pass = BlockingPass(columns=req.blocking_keys)
        naive_comps = len(left_df) * len(right_df)
        cands, b_report = generate_candidate_pairs(left_df, right_df, [b_pass])

        # Ground truth correspondence (used strictly in evaluation, never in linkage)
        true_pairs = build_true_pairs(
            state.bundle.ground_truth, req.left_dataset, req.right_dataset
        )
        total_true = len(true_pairs)
        b_eval = evaluate_blocking(cands, true_pairs, naive_comparisons=naive_comps)

        # Specs
        specs = [
            AttributeComparatorSpec(
                attribute=a, method="jaro_winkler", weight=1.0
            )
            for a in req.attributes
        ]

        # Fellegi-Sunter calibration
        fs_params = estimate_m_u_from_ground_truth(
            left_df=left_df,
            right_df=right_df,
            candidate_pairs=cands,
            truth=state.bundle.ground_truth,
            left_dataset=req.left_dataset,
            right_dataset=req.right_dataset,
            attributes=req.attributes,
        )

        def _evaluate_method(
            method_name: str,
            preds_df: pd.DataFrame,
            runtime_sec: float,
            thresh: float | None = None,
        ) -> dict[str, Any]:
            eval_res = evaluate_linkage_predictions(
                preds_df, true_pairs, total_true_pairs=total_true
            )
            reid_res = reidentification_success_rate(
                preds_df,
                state.bundle.ground_truth,
                left_dataset=req.left_dataset,
                right_dataset=req.right_dataset,
            )
            matches_count = int((preds_df["decision"] == "match").sum())
            return {
                "method": method_name,
                "threshold": thresh,
                "matches_predicted": matches_count,
                "true_positives": eval_res.true_positives,
                "false_positives": eval_res.false_positives,
                "false_negatives": eval_res.false_negatives,
                "precision": float(eval_res.precision or 0.0),
                "recall": float(eval_res.recall or 0.0),
                "f1_score": float(eval_res.f1_score or 0.0),
                "f1": float(eval_res.f1_score or 0.0),
                "tie_adjusted_reid_success": float(
                    reid_res.tie_adjusted_success_rate or 0.0
                ),
                "deterministic_reid_success": float(
                    reid_res.deterministic_success_rate or 0.0
                ),
                "reidentification_success": float(
                    reid_res.tie_adjusted_success_rate or 0.0
                ),
                "runtime_seconds": float(runtime_sec),
            }

        methods_summary: list[dict[str, Any]] = []

        if req.method in ("deterministic", "compare_all"):
            t0 = time.perf_counter()
            d_preds = deterministic_linkage(
                left_df,
                right_df,
                cands,
                attributes=req.attributes,
                left_name=req.left_dataset,
                right_name=req.right_dataset,
            )
            t_det = time.perf_counter() - t0
            methods_summary.append(
                _evaluate_method(
                    "Deterministic (Exact)", d_preds, t_det, thresh=1.0
                )
            )

        if req.method in ("similarity", "compare_all"):
            t0 = time.perf_counter()
            s_preds = similarity_linkage(
                left_df,
                right_df,
                cands,
                specs,
                threshold=req.threshold,
                left_name=req.left_dataset,
                right_name=req.right_dataset,
            )
            t_sim = time.perf_counter() - t0
            methods_summary.append(
                _evaluate_method(
                    "Similarity (Jaro-Winkler)",
                    s_preds,
                    t_sim,
                    thresh=req.threshold,
                )
            )

        if req.method in ("fellegi_sunter", "compare_all"):
            t0 = time.perf_counter()
            fs_preds = fellegi_sunter_linkage(
                left_df,
                right_df,
                cands,
                specs,
                params=fs_params,
                lower_threshold=-1.0,
                upper_threshold=1.0,
                left_name=req.left_dataset,
                right_name=req.right_dataset,
            )
            t_fs = time.perf_counter() - t0
            methods_summary.append(
                _evaluate_method(
                    "Fellegi-Sunter", fs_preds, t_fs, thresh=0.0
                )
            )

        state.stage_status["6. Linkage Engine"] = "done"
        state.stage_status["8. Evaluator"] = "done"

        primary = methods_summary[0] if methods_summary else {}

        return {
            "run_id": run_id,
            "left_dataset": req.left_dataset,
            "right_dataset": req.right_dataset,
            "method": req.method,
            "threshold": req.threshold,
            "candidate_pairs_count": len(cands),
            "reduction_ratio": b_report.reduction_ratio,
            "precision": primary.get("precision"),
            "recall": primary.get("recall"),
            "f1": primary.get("f1"),
            "f1_score": primary.get("f1_score"),
            "reidentification_success": primary.get("reidentification_success"),
            "tie_adjusted_reid_success": primary.get("tie_adjusted_reid_success"),
            "deterministic_reid_success": primary.get(
                "deterministic_reid_success"
            ),
            "runtime_seconds": primary.get("runtime_seconds"),
            "blocking": {
                "keys": req.blocking_keys,
                "candidate_pairs_count": len(cands),
                "naive_comparisons": naive_comps,
                "reduction_ratio": b_report.reduction_ratio,
                "pairs_completeness": b_eval.pairs_completeness,
            },
            "methods": methods_summary,
            "comparison": {m["method"]: m for m in methods_summary},
            "stage_status": state.stage_status,
        }

    def mitigate(
        self, run_id: str, req: MitigationRequest
    ) -> dict[str, Any]:
        """Execute privacy mitigation and compare before/after metrics."""
        state = self._get_run(run_id)
        if req.dataset_name not in state.bundle.datasets:
            raise ValidationError(
                f"Dataset '{req.dataset_name}' not found in run."
            )

        orig_df = state.bundle.datasets[req.dataset_name]

        # Before stats
        eq_before = build_equivalence_classes(orig_df, qi_columns=req.qi_columns)
        risk_before = calculate_class_risk(eq_before)
        r_before = {m.name: m.value for m in risk_before.metrics}

        specs: list[TransformationSpec] = []
        for t in req.transformations:
            kind = (
                t.get("kind")
                or t.get("type")
                or t.get("name")
                or "generalize_age"
            )
            raw_params = dict(t.get("parameters") or t.get("kwargs") or {})
            if kind == "generalize_age":
                if "column" not in raw_params:
                    raw_params["column"] = (
                        "age" if "age" in orig_df.columns else req.qi_columns[0]
                    )
                if "bin_width" not in raw_params:
                    raw_params["bin_width"] = 5
            elif kind == "suppress_rare_values":
                if "column" not in raw_params:
                    raw_params["column"] = (
                        "city"
                        if "city" in orig_df.columns
                        else req.qi_columns[0]
                    )
                if "minimum_frequency" not in raw_params:
                    raw_params["minimum_frequency"] = int(
                        raw_params.pop("min_count", 2)
                    )
                else:
                    raw_params.pop("min_count", None)
            elif kind == "coarsen_timestamp":
                if "column" not in raw_params:
                    raw_params["column"] = (
                        "timestamp"
                        if "timestamp" in orig_df.columns
                        else req.qi_columns[0]
                    )
                if "level" not in raw_params:
                    raw_params["level"] = "day"
            specs.append(
                TransformationSpec(kind=str(kind), parameters=raw_params)
            )
        mit_report = run_mitigation_experiment(
            orig_df, specs=specs, qi_columns=req.qi_columns
        )

        cur_df = orig_df.copy(deep=True)
        for tx in specs:
            if tx.kind == "generalize_age":
                cur_df = generalize_age(cur_df, **tx.parameters).df
            elif tx.kind == "coarsen_timestamp":
                cur_df = coarsen_timestamp(cur_df, **tx.parameters).df
            elif tx.kind == "suppress_rare_values":
                cur_df = suppress_rare_values(cur_df, **tx.parameters).df

        mit_df = cur_df
        eq_after = build_equivalence_classes(mit_df, qi_columns=req.qi_columns)
        risk_after = calculate_class_risk(eq_after)
        r_after = {m.name: m.value for m in risk_after.metrics}

        # Attacker success before/after
        atk_prof = AttackerProfile(
            name="mit_eval", steps=[tuple(req.qi_columns)]
        )
        atk_b = simulate_attack(
            orig_df,
            atk_prof,
            n_targets=min(30, len(orig_df)),
            seed=state.seed,
        )
        atk_a = simulate_attack(
            mit_df,
            atk_prof,
            n_targets=min(30, len(mit_df)),
            seed=state.seed,
        )

        common_cols = [
            c for c in orig_df.columns if c in mit_df.columns and c != "record_id"
        ]
        diff_cells = sum(
            int((orig_df[c].astype(str) != mit_df[c].astype(str)).sum())
            for c in common_cols
        )
        tot_cells = len(orig_df) * max(1, len(common_cols))
        utility_loss = diff_cells / tot_cells if tot_cells > 0 else 0.0

        state.stage_status["7. Mitigation"] = "done"

        b_uniq = (
            r_before.get("uniqueness_proportion")
            or r_before.get("uniqueness")
            or eq_before.singleton_record_proportion
            or 0.0
        )
        a_uniq = (
            r_after.get("uniqueness_proportion")
            or r_after.get("uniqueness")
            or eq_after.singleton_record_proportion
            or 0.0
        )

        b_dict = {
            "k_anonymity": eq_before.k,
            "k": eq_before.k,
            "singleton_proportion": float(b_uniq),
            "uniqueness": float(r_before.get("uniqueness") or 0.0),
            "max_risk": float(r_before.get("max_class_risk") or 0.0),
            "max_class_risk": float(r_before.get("max_class_risk") or 0.0),
            "average_risk": float(r_before.get("average_class_risk") or 0.0),
            "average_class_risk": float(
                r_before.get("average_class_risk") or 0.0
            ),
            "discernibility_metric": int(
                r_before.get("discernibility_metric") or 0
            ),
        }
        a_dict = {
            "k_anonymity": eq_after.k,
            "k": eq_after.k,
            "singleton_proportion": float(a_uniq),
            "uniqueness": float(r_after.get("uniqueness") or 0.0),
            "max_risk": float(r_after.get("max_class_risk") or 0.0),
            "max_class_risk": float(r_after.get("max_class_risk") or 0.0),
            "average_risk": float(r_after.get("average_class_risk") or 0.0),
            "average_class_risk": float(
                r_after.get("average_class_risk") or 0.0
            ),
            "discernibility_metric": int(
                r_after.get("discernibility_metric") or 0
            ),
        }

        return {
            "run_id": run_id,
            "dataset_name": req.dataset_name,
            "qi_columns": req.qi_columns,
            "transformations_applied": len(specs),
            "before": b_dict,
            "after": a_dict,
            "privacy_comparison": {
                "before": b_dict,
                "after": a_dict,
            },
            "utility": {
                "suppression_fraction": mit_report.suppression_fraction,
                "suppression_rate": mit_report.suppression_fraction,
                "records_suppressed": int(
                    mit_report.suppression_fraction * len(orig_df)
                ),
                "discernibility_metric": float(
                    r_after.get("discernibility_metric") or 0.0
                ),
                "cell_utility_loss": float(utility_loss),
                "dm_change": int(
                    (r_after.get("discernibility_metric") or 0)
                    - (r_before.get("discernibility_metric") or 0)
                ),
            },
            "attacker_comparison": {
                "before_mean_risk": atk_b.step_reports[-1].mean_risk,
                "after_mean_risk": atk_a.step_reports[-1].mean_risk,
                "before_unique_fraction": atk_b.step_reports[-1].unique_fraction,
                "after_unique_fraction": atk_a.step_reports[-1].unique_fraction,
            },
            "notes": (
                "Privacy mitigation creates larger equivalence classes, "
                "lowering unique re-identification risk. Note that average risk "
                "may remain unchanged if already generalized classes cannot be "
                "further partitioned without record suppression."
            ),
            "stage_status": state.stage_status,
        }

    def run_pipeline(self, run_id: str) -> dict[str, Any]:
        """Execute the complete 9-stage pipeline and return structured audit report."""
        state = self._get_run(run_id)
        config = PipelineConfig(
            seed=state.seed,
            generator_preset=state.preset,
            population_size=state.population_size,
            shared_fraction=state.shared_fraction,
            typo_rate=state.typo_rate,
            missing_rate=state.missing_rate,
        )
        report = run_pipeline_orchestrator(config)
        for k in state.stage_status:
            state.stage_status[k] = "done"
        res = report.to_dict()
        res["stage_status"] = state.stage_status
        return res

    def get_tables(self, run_id: str) -> dict[str, Any]:
        """Retrieve real benchmark Tables 5, 6, and 7 executed for this run."""
        state = self._get_run(run_id)
        n = state.population_size
        seed = state.seed
        f = state.shared_fraction

        df5, md5, csv5 = run_table5_experiment(
            n=n, seed=seed, targets_count=min(50, n)
        )
        df6, md6, csv6 = run_table6_experiment(
            n=n, shared_fraction=f, seed=seed
        )
        df7, md7, csv7 = run_table7_experiment(
            n=n, shared_fraction=f, seed=seed
        )

        return {
            "run_id": run_id,
            "population_size": n,
            "seed": seed,
            "table5": {
                "title": "Table 5: Progressive Attacker Simulator",
                "rows": df5.to_dict(orient="records"),
                "markdown": md5,
                "csv": csv5,
            },
            "table6": {
                "title": "Table 6: Linkage Methods Benchmark",
                "rows": df6.to_dict(orient="records"),
                "markdown": md6,
                "csv": csv6,
            },
            "table7": {
                "title": "Table 7: Mitigation Privacy-Utility Tradeoffs",
                "rows": df7.to_dict(orient="records"),
                "markdown": md7,
                "csv": csv7,
            },
        }


demo_service = DemoService()

