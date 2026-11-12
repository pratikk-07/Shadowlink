"""Privacy-Utility evaluation and before/after metric comparison."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.mitigation.models import MitigationReport, TransformationLogEntry
from shadowlink.qi_analyser.equivalence import build_equivalence_classes
from shadowlink.risk.metrics import calculate_class_risk


def calculate_profile_dict(
    df: pd.DataFrame, qi_columns: Sequence[str]
) -> dict[str, Any]:
    """Calculate key privacy and granularity metrics for a dataset."""
    eq = build_equivalence_classes(df, qi_columns=qi_columns)
    risk_report = calculate_class_risk(eq)
    metric_map = {m.name: m.value for m in risk_report.metrics}

    return {
        "record_count": len(df),
        "num_classes": eq.num_classes,
        "k": eq.k,
        "uniqueness": metric_map.get("uniqueness"),
        "max_class_risk": metric_map.get("max_class_risk"),
        "average_class_risk": metric_map.get("average_class_risk"),
        "discernibility_metric": metric_map.get("discernibility_metric"),
    }


def compare_privacy_utility(
    original: pd.DataFrame,
    transformed: pd.DataFrame,
    qi_columns: Sequence[str],
    queries: Mapping[str, Callable[[pd.DataFrame], Any]] | None = None,
    transformation_logs: list[TransformationLogEntry] | None = None,
) -> MitigationReport:
    """Compare privacy indicators and utility retention before and after mitigation."""
    for col in qi_columns:
        if col not in original.columns:
            raise ValidationError(f"QI column '{col}' missing from original DataFrame.")
        if col not in transformed.columns:
            raise ValidationError(
                f"QI column '{col}' missing from transformed DataFrame."
            )

    before_stats = calculate_profile_dict(original, qi_columns)
    after_stats = calculate_profile_dict(transformed, qi_columns)

    # Calculate suppression fraction (records suppressed)
    orig_n = len(original)
    trans_n = len(transformed)
    records_suppressed = max(0, orig_n - trans_n)
    sup_frac = (records_suppressed / orig_n) if orig_n > 0 else 0.0

    # Execute analytical queries if provided
    query_answers: dict[str, tuple[Any, Any]] = {}
    if queries:
        for q_name, q_func in queries.items():
            ans_before = q_func(original)
            ans_after = q_func(transformed)
            query_answers[q_name] = (ans_before, ans_after)

    return MitigationReport(
        before=before_stats,
        after=after_stats,
        suppression_fraction=sup_frac,
        query_answers=query_answers,
        transformation_logs=transformation_logs or [],
    )
