"""Risk metric computations under the prosecutor attacker model."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.schemas import AttackerStepSummary
from shadowlink.qi_analyser.equivalence import discernibility_metric
from shadowlink.qi_analyser.models import EquivalenceClassResult
from shadowlink.risk.candidate_models import (
    CandidateRiskReport,
    CandidateStepRisk,
)
from shadowlink.risk.models import RiskMetric, RiskReport


def calculate_class_risk(classes: EquivalenceClassResult) -> RiskReport:
    """Compute explainable privacy risk metrics from equivalence class results.

    Parameters
    ----------
    classes:
        EquivalenceClassResult produced by build_equivalence_classes.

    Returns
    -------
    RiskReport
        Collection of named risk indicators and per-record risk probabilities.
    """
    k_val = classes.k
    n = classes.records_analysed
    num_classes = classes.num_classes

    # 1. k-anonymity metric
    k_metric = RiskMetric(
        name="k_anonymity",
        value=float(k_val) if k_val is not None else None,
        denominator="none",
        formula="k = min(|EC_i|)",
        assumption=(
            "Prosecutor model; attacker knows target is in the data. "
            "All records in an equivalence class are indistinguishable on QIs."
        ),
        source_module="qi_analyser.equivalence",
        explanation=(
            "Minimum number of records in any equivalence class. "
            "A dataset has k-anonymity if each class contains at least k records."
        ),
    )

    # 2. Maximum class risk = 1 / k
    if k_val is not None and k_val > 0:
        max_risk_val = float(1.0 / k_val)
    else:
        max_risk_val = None

    max_risk_metric = RiskMetric(
        name="max_class_risk",
        value=max_risk_val,
        denominator="k",
        formula="max_class_risk = 1 / k",
        assumption=(
            "Prosecutor model; attacker knows target is present and targets "
            "the record belonging to the smallest equivalence class."
        ),
        source_module="risk.metrics",
        explanation=(
            "Upper bound on re-identification probability for any individual "
            "in the dataset."
        ),
    )

    # 3. Average class risk = num_classes / records_analysed
    if n > 0:
        avg_risk_val = float(num_classes / n)
    else:
        avg_risk_val = None

    avg_risk_metric = RiskMetric(
        name="average_class_risk",
        value=avg_risk_val,
        denominator="records_analysed",
        formula="average_class_risk = num_classes / records_analysed",
        assumption=(
            "Prosecutor model; attacker picks a target uniformly at random "
            "from the dataset."
        ),
        source_module="risk.metrics",
        explanation=(
            "Expected re-identification probability averaged over all records "
            "in the dataset."
        ),
    )

    # 4. Uniqueness (proportion of singleton records)
    uniq_val = classes.singleton_record_proportion
    uniqueness_metric = RiskMetric(
        name="uniqueness",
        value=float(uniq_val) if uniq_val is not None else None,
        denominator="records_analysed",
        formula="uniqueness = singleton_record_count / records_analysed",
        assumption=(
            "Prosecutor model; singletons (classes of size 1) can be "
            "re-identified with 100% certainty if matched."
        ),
        source_module="risk.metrics",
        explanation=(
            "Proportion of records that belong to singleton equivalence classes."
        ),
    )

    # 5. Discernibility Metric
    dm_val = float(discernibility_metric(classes))
    dm_metric = RiskMetric(
        name="discernibility_metric",
        value=dm_val,
        denominator="none",
        formula="discernibility_metric = sum(|EC_i|^2)",
        assumption=(
            "Prosecutor model; larger class sizes improve k-anonymity "
            "at the expense of data granularity."
        ),
        source_module="risk.metrics",
        explanation=("Penalty metric based on sum of squared equivalence class sizes."),
    )

    # Compute per-record risk Series: 1 / f_i
    # For excluded records (size == 0), per-record risk is 0.0 or None
    raw_sizes = classes.record_class_sizes
    per_record_risk = pd.Series(0.0, index=raw_sizes.index, dtype="float64")
    mask_analysed = raw_sizes > 0
    if mask_analysed.any():
        rec_vals = 1.0 / raw_sizes.loc[mask_analysed]
        per_record_risk.loc[mask_analysed] = rec_vals.astype("float64")

    metrics_list = [
        k_metric,
        max_risk_metric,
        avg_risk_metric,
        uniqueness_metric,
        dm_metric,
    ]

    return RiskReport(
        metrics=metrics_list,
        per_record_risk=per_record_risk,
    )


def calculate_candidate_risk(
    candidate_counts: Sequence[int],
    initial_count: int,
) -> CandidateRiskReport:
    """Calculate risk and reduction metrics across candidate narrowing steps.

    Parameters
    ----------
    candidate_counts:
        Sequence of candidate set sizes |C_j| after revealing attributes.
    initial_count:
        Initial total population or dataset record count (|C_0|).

    Returns
    -------
    CandidateRiskReport
    """
    if initial_count <= 0:
        raise ValidationError(f"initial_count must be > 0, got {initial_count}.")

    steps: list[CandidateStepRisk] = []
    for step_idx, count in enumerate(candidate_counts):
        if count < 0:
            raise ValidationError(
                f"Candidate count at step {step_idx} cannot be negative, got {count}."
            )
        if count > initial_count:
            raise ValidationError(
                f"Candidate count ({count}) cannot exceed "
                f"initial_count ({initial_count}) at step {step_idx}."
            )

        reduction = 1.0 - (count / initial_count)

        if count == 0:
            risk: float | None = None
            explanation = "No candidates match the specified attributes."
        else:
            risk = 1.0 / count
            explanation = (
                f"Candidate set narrowed to {count}; "
                f"re-identification probability is 1/{count}."
            )

        steps.append(
            CandidateStepRisk(
                step=step_idx,
                candidate_count=count,
                risk=risk,
                candidate_reduction=reduction,
                explanation=explanation,
            )
        )

    return CandidateRiskReport(initial_count=initial_count, steps=steps)


def calculate_candidate_risk_from_steps(
    steps: Sequence[AttackerStepSummary],
    initial_count: int,
) -> CandidateRiskReport:
    """Calculate candidate-set risk from Attacker Simulator summary steps."""
    counts = [s.candidate_count for s in steps]
    return calculate_candidate_risk(counts, initial_count=initial_count)
