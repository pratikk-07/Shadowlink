"""Command Line Interface for SHADOWLINK."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

from shadowlink.attacker.models import AttackerProfile
from shadowlink.attacker.simulator import simulate_attack
from shadowlink.common.exceptions import ShadowlinkError
from shadowlink.evaluator.experiments import (
    run_table5_experiment,
    run_table6_experiment,
    run_table7_experiment,
)
from shadowlink.evaluator.ground_truth import build_true_pairs, load_ground_truth
from shadowlink.evaluator.metrics import evaluate_linkage_predictions
from shadowlink.generator.generator import report_abc, wide_release
from shadowlink.generator.io import write_bundle
from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.methods import deterministic_linkage, similarity_linkage
from shadowlink.linkage.models import AttributeComparatorSpec
from shadowlink.mitigation.models import TransformationSpec
from shadowlink.mitigation.pipeline import run_mitigation_experiment
from shadowlink.pipeline import PipelineConfig, run_pipeline
from shadowlink.profiler.profiler import profile_csv
from shadowlink.qi_analyser.candidates import find_candidate_qis
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.qi_analyser.models import MissingPolicy
from shadowlink.qi_analyser.overlap import find_shared_attributes
from shadowlink.risk.metrics import calculate_class_risk


def create_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="shadowlink",
        description="SHADOWLINK: Privacy Re-identification Risk Platform",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. profile
    p_prof = subparsers.add_parser("profile", help="Profile a tabular dataset")
    p_prof.add_argument("path", help="Path to CSV dataset")
    p_prof.add_argument("--name", default=None, help="Optional dataset name")
    p_prof.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_prof.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 2. classes
    p_cls = subparsers.add_parser(
        "classes", help="Compute equivalence classes over QIs"
    )
    p_cls.add_argument("path", help="Path to CSV dataset")
    p_cls.add_argument(
        "--qi", required=True, help="Comma-separated quasi-identifier column names"
    )
    p_cls.add_argument(
        "--missing-policy",
        choices=["own_group", "exclude_records"],
        default="own_group",
        help="Missing value policy",
    )
    p_cls.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_cls.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 3. risk
    p_risk = subparsers.add_parser(
        "risk", help="Evaluate re-identification risk metrics"
    )
    p_risk.add_argument("path", help="Path to CSV dataset")
    p_risk.add_argument(
        "--qi", required=True, help="Comma-separated quasi-identifier column names"
    )
    p_risk.add_argument(
        "--missing-policy",
        choices=["own_group", "exclude_records"],
        default="own_group",
        help="Missing value policy",
    )
    p_risk.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_risk.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 4. candidates
    p_cand = subparsers.add_parser(
        "candidates", help="Detect candidate quasi-identifiers"
    )
    p_cand.add_argument("paths", nargs="+", help="One or more CSV dataset paths")
    p_cand.add_argument(
        "--threshold", type=float, default=0.5, help="Uniqueness ratio threshold"
    )
    p_cand.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_cand.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 5. shared
    p_shared = subparsers.add_parser(
        "shared", help="Find shared attributes across multiple datasets"
    )
    p_shared.add_argument("paths", nargs="+", help="Two or more CSV dataset paths")
    p_shared.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_shared.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 6. mitigate
    p_mit = subparsers.add_parser("mitigate", help="Run privacy mitigation pipeline")
    p_mit.add_argument("path", help="Path to CSV dataset")
    p_mit.add_argument(
        "--qi", required=True, help="Comma-separated quasi-identifier column names"
    )
    p_mit.add_argument(
        "--config",
        required=True,
        help="JSON configuration file with transformation specs",
    )
    p_mit.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_mit.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 7. generate
    p_gen = subparsers.add_parser("generate", help="Generate synthetic bundle")
    p_gen.add_argument(
        "--preset",
        choices=["report_abc", "wide_release"],
        default="report_abc",
        help="Dataset bundle preset",
    )
    p_gen.add_argument("--n", type=int, default=500, help="Population size")
    p_gen.add_argument(
        "--shared-fraction",
        type=float,
        default=0.5,
        help="Fraction of shared people",
    )
    p_gen.add_argument("--seed", type=int, default=42, help="Random seed")
    p_gen.add_argument(
        "--out-dir", required=True, help="Destination directory for CSVs and manifest"
    )

    # 8. link
    p_link = subparsers.add_parser("link", help="Link records between two datasets")
    p_link.add_argument("left_path", help="Left dataset CSV path")
    p_link.add_argument("right_path", help="Right dataset CSV path")
    p_link.add_argument(
        "--method",
        choices=["deterministic", "similarity"],
        default="similarity",
        help="Linkage method",
    )
    p_link.add_argument(
        "--attributes",
        required=True,
        help="Comma-separated attribute names to compare",
    )
    p_link.add_argument(
        "--blocking-keys",
        default=None,
        help="Optional comma-separated blocking key attributes",
    )
    p_link.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Linkage score decision threshold",
    )
    p_link.add_argument("--output", required=True, help="Destination CSV path")

    # 9. attack
    p_atk = subparsers.add_parser("attack", help="Simulate re-identification attack")
    p_atk.add_argument("path", help="Target dataset CSV path")
    p_atk.add_argument(
        "--target-id", default=None, help="Optional target record_id"
    )
    p_atk.add_argument(
        "--aux",
        default=None,
        help="Optional JSON object of auxiliary attributes",
    )
    p_atk.add_argument(
        "--steps",
        default="age,city;course;location;timestamp",
        help="Semicolon-separated steps of comma-separated attributes",
    )

    # 10. evaluate
    p_eval = subparsers.add_parser(
        "evaluate", help="Evaluate linkage predictions against ground truth"
    )
    p_eval.add_argument("predictions_path", help="Path to scored predictions CSV")
    p_eval.add_argument("ground_truth_path", help="Path to ground truth CSV")
    p_eval.add_argument(
        "--left-dataset", default="A", help="Name of left dataset in ground truth"
    )
    p_eval.add_argument(
        "--right-dataset", default="B", help="Name of right dataset in ground truth"
    )
    p_eval.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    p_eval.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 11. experiment
    p_exp = subparsers.add_parser("experiment", help="Run benchmark experiment")
    p_exp.add_argument(
        "table",
        choices=["table5", "table6", "table7"],
        help="Experiment table to run",
    )
    p_exp.add_argument("--n", type=int, default=500, help="Population size")
    p_exp.add_argument(
        "--shared-fraction",
        type=float,
        default=0.5,
        help="Fraction of shared people",
    )
    p_exp.add_argument("--seed", type=int, default=42, help="Random seed")
    p_exp.add_argument(
        "--format", choices=["markdown", "csv"], default="markdown", help="Format"
    )
    p_exp.add_argument(
        "--output", default=None, help="Optional output file destination"
    )

    # 12. run-pipeline
    p_pipe = subparsers.add_parser(
        "run-pipeline",
        help="Execute end-to-end 9-stage pipeline connecting all modules",
    )
    p_pipe.add_argument(
        "--config",
        required=True,
        help="Path to pipeline JSON configuration file",
    )
    p_pipe.add_argument(
        "--out",
        required=True,
        help="Destination directory for report.json and report.md",
    )

    return parser


def emit_output(content: str, output_path: str | None) -> None:
    """Print or write content to destination."""
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content + "\n")


def handle_profile(args: argparse.Namespace) -> int:
    prof = profile_csv(args.path, dataset_name=args.name)
    if args.format == "json":
        emit_output(prof.to_json(), args.output)
    else:
        lines = [
            f"Profile for '{prof.dataset_name}':",
            f"  rows: {prof.row_count}",
            f"  columns: {prof.column_count}",
            f"  duplicate_row_count: {prof.duplicate_row_count}",
            f"  memory_bytes: {prof.memory_bytes}",
            "Columns:",
        ]
        for c in prof.columns:
            u_str = f"{c.uniqueness_ratio:.3f}" if c.uniqueness_ratio else "None"
            lines.append(
                f"  - {c.name}: {c.kind} ({c.dtype}), distinct: {c.distinct_count}, "
                f"uniqueness: {u_str}, missing: {c.missing_count}"
            )
        emit_output("\n".join(lines), args.output)
    return 0


def handle_classes(args: argparse.Namespace) -> int:
    qi_cols = [c.strip() for c in args.qi.split(",") if c.strip()]
    df = pd.read_csv(args.path)
    policy: MissingPolicy = args.missing_policy
    eq = build_equivalence_classes(df, qi_columns=qi_cols, missing_policy=policy)
    if args.format == "json":
        emit_output(json.dumps(eq.to_dict(), indent=2), args.output)
    else:
        p_str = (
            f"{eq.singleton_record_proportion:.2%}"
            if eq.singleton_record_proportion is not None
            else "None"
        )
        lines = [
            f"Equivalence Classes on {eq.qi_columns}:",
            f"  records_analysed: {eq.records_analysed}",
            f"  num_classes: {eq.num_classes}",
            f"  k: {eq.k}",
            f"  singleton_classes: {eq.singleton_class_count}",
            f"  singleton_records: {eq.singleton_record_count} ({p_str})",
            f"  top_class_sizes: {eq.class_sizes[:5]}",
        ]
        emit_output("\n".join(lines), args.output)
    return 0


def handle_risk(args: argparse.Namespace) -> int:
    qi_cols = [c.strip() for c in args.qi.split(",") if c.strip()]
    df = pd.read_csv(args.path)
    policy: MissingPolicy = args.missing_policy
    eq = build_equivalence_classes(df, qi_columns=qi_cols, missing_policy=policy)
    report = calculate_class_risk(eq)
    if args.format == "json":
        emit_output(report.to_json(), args.output)
    else:
        lines = ["Privacy Risk Report (Prosecutor Model):"]
        for m in report.metrics:
            val_str = f"{m.value:.4f}" if m.value is not None else "None"
            lines.append(f"  - {m.name}: {val_str} ({m.formula})")
        emit_output("\n".join(lines), args.output)
    return 0


def handle_candidates(args: argparse.Namespace) -> int:
    profiles = [profile_csv(p) for p in args.paths]
    from shadowlink.qi_analyser.models import QIHeuristics

    heuristics = QIHeuristics(high_uniqueness_threshold=args.threshold)
    candidates = find_candidate_qis(profiles, heuristics=heuristics)
    if args.format == "json":
        res = [
            {
                "column_name": c.column_name,
                "dataset_name": c.dataset_name,
                "uniqueness_ratio": c.uniqueness_ratio,
                "reasons": c.reasons,
                "status": c.status,
            }
            for c in candidates
        ]
        emit_output(json.dumps(res, indent=2), args.output)
    else:
        lines = [f"Found {len(candidates)} candidate quasi-identifier(s):"]
        for c in candidates:
            lines.append(
                f"  - {c.column_name} (in '{c.dataset_name}'): {', '.join(c.reasons)}"
            )
        emit_output("\n".join(lines), args.output)
    return 0


def handle_shared(args: argparse.Namespace) -> int:
    profiles = [profile_csv(p) for p in args.paths]
    shared_map = find_shared_attributes(profiles)
    if args.format == "json":
        res = {
            canon: [
                {
                    "dataset_name": e.dataset_name,
                    "original_name": e.original_name,
                    "kind": e.kind,
                    "dtype_compatible": e.dtype_compatible,
                }
                for e in entries
            ]
            for canon, entries in shared_map.items()
        }
        emit_output(json.dumps(res, indent=2), args.output)
    else:
        lines = [f"Found {len(shared_map)} shared attribute(s):"]
        for canon, entries in shared_map.items():
            locs = [f"{e.dataset_name}: '{e.original_name}'" for e in entries]
            lines.append(f"  - {canon}: shared across {', '.join(locs)}")
        emit_output("\n".join(lines), args.output)
    return 0


def handle_mitigate(args: argparse.Namespace) -> int:
    qi_cols = [c.strip() for c in args.qi.split(",") if c.strip()]
    df = pd.read_csv(args.path)

    cfg_raw = json.loads(Path(args.config).read_text(encoding="utf-8"))
    specs = [
        TransformationSpec(kind=item["kind"], parameters=item["parameters"])
        for item in cfg_raw
    ]

    report = run_mitigation_experiment(df, specs=specs, qi_columns=qi_cols)
    if args.format == "json":
        emit_output(report.to_json(), args.output)
    else:
        b_u = report.before['uniqueness']
        a_u = report.after['uniqueness']
        b_dm = report.before["discernibility_metric"]
        a_dm = report.after["discernibility_metric"]
        lines = [
            "Mitigation Report:",
            f"  Before: k={report.before['k']}, uniqueness={b_u:.3f}, DM={b_dm}",
            f"  After:  k={report.after['k']}, uniqueness={a_u:.3f}, DM={a_dm}",
            f"  Records Suppressed Fraction: {report.suppression_fraction:.2%}",
            f"  Transformations applied: {len(report.transformation_logs)}",
        ]
        emit_output("\n".join(lines), args.output)
    return 0


def handle_generate(args: argparse.Namespace) -> int:
    if args.preset == "wide_release":
        bundle = wide_release(seed=args.seed, population_size=args.n)
    else:
        bundle = report_abc(
            seed=args.seed,
            population_size=args.n,
            shared_fraction=args.shared_fraction,
        )
    out_dir = Path(args.out_dir)
    write_bundle(bundle, out_dir)
    lines = [
        f"Generated {args.preset} bundle at '{out_dir}':",
        f"  Total records: {sum(len(df) for df in bundle.datasets.values())}",
        f"  Datasets: {list(bundle.datasets.keys())}",
    ]
    emit_output("\n".join(lines), None)
    return 0


def handle_link(args: argparse.Namespace) -> int:
    left_df = pd.read_csv(args.left_path)
    right_df = pd.read_csv(args.right_path)
    attrs = [a.strip() for a in args.attributes.split(",") if a.strip()]

    if args.blocking_keys:
        b_keys = [k.strip() for k in args.blocking_keys.split(",") if k.strip()]
        b_pass = BlockingPass(columns=b_keys)
        cands, _ = generate_candidate_pairs(left_df, right_df, [b_pass])
    else:
        rows = [
            {"left_id": str(l_id), "right_id": str(r_id)}
            for l_id in left_df["record_id"]
            for r_id in right_df["record_id"]
        ]
        cands = pd.DataFrame(rows)

    if args.method == "deterministic":
        preds = deterministic_linkage(left_df, right_df, cands, attributes=attrs)
    else:
        specs = [
            AttributeComparatorSpec(attribute=a, method="jaro_winkler", weight=1.0)
            for a in attrs
        ]
        preds = similarity_linkage(
            left_df, right_df, cands, specs, threshold=args.threshold
        )

    preds.to_csv(args.output, index=False)
    emit_output(f"Wrote {len(preds)} scored pairs to '{args.output}'", None)
    return 0


def handle_attack(args: argparse.Namespace) -> int:
    df = pd.read_csv(args.path)

    if args.steps:
        step_tuples = [
            tuple(s.strip() for s in step.split(",") if s.strip())
            for step in args.steps.split(";")
            if step.strip()
        ]
    else:
        step_tuples = [("age", "city")]

    profile = AttackerProfile(name="cli_attack", steps=step_tuples)
    res = simulate_attack(df, profile=profile, n_targets=min(50, len(df)), seed=42)

    lines = [f"Attack Simulation for profile '{profile.name}':"]
    for s in res.step_reports:
        lines.append(
            f"  Step {s.step} {s.attributes}: "
            f"mean_candidates={s.mean_candidates:.2f}, "
            f"mean_risk={s.mean_risk:.4f}, unique_fraction={s.unique_fraction:.4f}"
        )
    emit_output("\n".join(lines), None)
    return 0


def handle_evaluate(args: argparse.Namespace) -> int:
    preds = pd.read_csv(args.predictions_path)
    gt = load_ground_truth(args.ground_truth_path)
    true_pairs = build_true_pairs(gt, args.left_dataset, args.right_dataset)

    eval_res = evaluate_linkage_predictions(
        preds, true_pairs, total_true_pairs=len(true_pairs)
    )

    if args.format == "json":
        emit_output(
            json.dumps(
                {
                    "precision": eval_res.precision,
                    "recall": eval_res.recall,
                    "f1_score": eval_res.f1_score,
                    "true_positives": eval_res.true_positives,
                    "false_positives": eval_res.false_positives,
                    "false_negatives": eval_res.false_negatives,
                },
                indent=2,
            ),
            args.output,
        )
    else:
        lines = [
            "Linkage Evaluation Results:",
            f"  Precision:       {eval_res.precision:.4f}",
            f"  Recall:          {eval_res.recall:.4f}",
            f"  F1 Score:        {eval_res.f1_score:.4f}",
            f"  True Positives:  {eval_res.true_positives}",
            f"  False Positives: {eval_res.false_positives}",
            f"  False Negatives: {eval_res.false_negatives}",
        ]
        emit_output("\n".join(lines), args.output)
    return 0


def handle_experiment(args: argparse.Namespace) -> int:
    if args.table == "table5":
        res_df, md, csv_str = run_table5_experiment(n=args.n, seed=args.seed)
    elif args.table == "table6":
        res_df, md, csv_str = run_table6_experiment(
            n=args.n, shared_fraction=args.shared_fraction, seed=args.seed
        )
    else:
        res_df, md, csv_str = run_table7_experiment(
            n=args.n, shared_fraction=args.shared_fraction, seed=args.seed
        )

    out = md if args.format == "markdown" else csv_str
    emit_output(out, args.output)
    return 0


def handle_run_pipeline(args: argparse.Namespace) -> int:
    cfg = PipelineConfig.from_json(args.config)
    _ = run_pipeline(cfg, out_dir=args.out)
    emit_output(
        f"Pipeline executed successfully. Reports written to '{args.out}'.",
        None,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = create_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    handlers = {
        "profile": handle_profile,
        "classes": handle_classes,
        "risk": handle_risk,
        "candidates": handle_candidates,
        "shared": handle_shared,
        "mitigate": handle_mitigate,
        "generate": handle_generate,
        "link": handle_link,
        "attack": handle_attack,
        "evaluate": handle_evaluate,
        "experiment": handle_experiment,
        "run-pipeline": handle_run_pipeline,
    }

    handler = handlers.get(args.subcommand)
    if not handler:
        sys.stderr.write(f"Unknown subcommand: {args.subcommand}\n")
        return 2

    try:
        return handler(args)
    except ShadowlinkError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"Unexpected error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
