"""Evaluator package for SHADOWLINK (Ground truth analysis and verification)."""

from shadowlink.evaluator.calibration import estimate_m_u_from_ground_truth
from shadowlink.evaluator.experiments import (
    run_table5_experiment,
    run_table6_experiment,
    run_table7_experiment,
)
from shadowlink.evaluator.ground_truth import build_true_pairs, load_ground_truth
from shadowlink.evaluator.metrics import (
    BlockingEvaluation,
    LinkageEvaluation,
    ReidentificationMetrics,
    evaluate_blocking,
    evaluate_linkage_predictions,
    reidentification_success_rate,
)
from shadowlink.evaluator.mitigation_eval import (
    MitigationTradeoffReport,
    evaluate_mitigation_linkage_tradeoff,
    evaluate_mitigation_on_dataset,
)
from shadowlink.evaluator.tables import (
    format_csv_with_header,
    format_markdown_table,
    generate_experiment_metadata,
)

__all__ = [
    "BlockingEvaluation",
    "LinkageEvaluation",
    "MitigationTradeoffReport",
    "ReidentificationMetrics",
    "build_true_pairs",
    "estimate_m_u_from_ground_truth",
    "evaluate_blocking",
    "evaluate_linkage_predictions",
    "evaluate_mitigation_linkage_tradeoff",
    "evaluate_mitigation_on_dataset",
    "format_csv_with_header",
    "format_markdown_table",
    "generate_experiment_metadata",
    "load_ground_truth",
    "reidentification_success_rate",
    "run_table5_experiment",
    "run_table6_experiment",
    "run_table7_experiment",
]
