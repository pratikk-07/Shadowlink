"""Risk explanations and qualitative interpretations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from shadowlink.risk.models import RiskReport

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "UNDEFINED"]


@dataclass(frozen=True)
class RiskExplanation:
    """Human-readable explanation of an individual risk metric."""

    metric_name: str
    level: RiskLevel
    summary: str
    details: str

    def to_dict(self) -> dict[str, Any]:
        """Convert explanation to dictionary."""
        return asdict(self)


def explain_risk(report: RiskReport) -> list[RiskExplanation]:
    """Generate structured explanations for all risk metrics in a RiskReport.

    Parameters
    ----------
    report:
        Computed RiskReport instance.

    Returns
    -------
    list[RiskExplanation]
        Detailed risk interpretations.
    """
    explanations: list[RiskExplanation] = []

    for metric in report.metrics:
        name = metric.name
        val = metric.value

        if val is None:
            explanations.append(
                RiskExplanation(
                    metric_name=name,
                    level="UNDEFINED",
                    summary=f"{name} is undefined (no analysable records).",
                    details=(
                        "Dataset contains 0 analysable records. "
                        "No risk can be computed."
                    ),
                )
            )
            continue

        if name == "k_anonymity":
            if val <= 1.0:
                lvl: RiskLevel = "CRITICAL"
                summary = "k=1: Dataset contains unique (singleton) records."
                details = (
                    "At least one record is uniquely identified by the chosen "
                    "quasi-identifiers. An attacker with auxiliary data can "
                    "re-identify the subject with 100% confidence."
                )
            elif val < 5.0:
                lvl = "MEDIUM"
                summary = f"k={int(val)}: Low anonymity protection."
                details = (
                    f"Smallest equivalence class contains {int(val)} records. "
                    "Attacker can narrow candidates to a small group."
                )
            else:
                lvl = "LOW"
                summary = f"k={int(val)}: Strong k-anonymity protection."
                details = (
                    f"Every record shares quasi-identifiers with at "
                    f"least {int(val) - 1} others."
                )

        elif name == "max_class_risk":
            if val >= 1.0:
                lvl = "CRITICAL"
                summary = "Maximum re-identification risk is 100%."
                details = (
                    "Prosecutor model: at least one record has 100% link certainty."
                )
            elif val >= 0.5:
                lvl = "HIGH"
                summary = f"Maximum re-identification risk is {val * 100:.1f}%."
                details = "Smallest group has 2 records, giving a 50% link probability."
            else:
                lvl = "LOW"
                summary = f"Maximum re-identification risk is {val * 100:.1f}%."
                details = "No individual class exceeds the risk threshold."

        elif name == "average_class_risk":
            if val >= 0.5:
                lvl = "HIGH"
                summary = (
                    f"Average re-identification risk is {val * 100:.1f}%."
                )
                details = (
                    "On average across the dataset, candidates are narrowed "
                    "to very few individuals."
                )
            elif val >= 0.2:
                lvl = "MEDIUM"
                summary = f"Average re-identification risk is {val * 100:.1f}%."
                details = "Moderate candidate narrowing across the population."
            else:
                lvl = "LOW"
                summary = f"Average re-identification risk is low ({val * 100:.1f}%)."
                details = (
                    "Equivalence classes are generally large across the entire dataset."
                )

        elif name == "uniqueness":
            if val > 0.5:
                lvl = "CRITICAL"
                summary = (
                    f"{val * 100:.1f}% of records are completely unique singletons."
                )
                details = (
                    "Majority of subjects are directly linkable by quasi-identifiers."
                )
            elif val > 0.0:
                lvl = "HIGH"
                summary = f"{val * 100:.1f}% of records are unique singletons."
                details = (
                    "Presence of singleton records violates strict k-anonymity (k=1)."
                )
            else:
                lvl = "LOW"
                summary = "No singleton records exist (0.0% uniqueness)."
                details = (
                    "All records belong to equivalence classes of size 2 or greater."
                )

        elif name == "discernibility_metric":
            lvl = "LOW" if val < 100 else "MEDIUM"
            summary = f"Discernibility Metric is {int(val)}."
            details = (
                "Sum of squared equivalence class sizes. Larger classes increase DM "
                "while reducing granularity."
            )
        else:
            lvl = "LOW"
            summary = f"{name} = {val}"
            details = metric.explanation

        explanations.append(
            RiskExplanation(
                metric_name=name,
                level=lvl,
                summary=summary,
                details=details,
            )
        )

    return explanations
