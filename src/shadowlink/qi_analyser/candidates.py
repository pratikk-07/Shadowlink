"""Quasi-identifier candidate identification and selection management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from shadowlink.common.normalization import normalize_column_name
from shadowlink.profiler.models import DatasetProfile
from shadowlink.qi_analyser.models import QICandidate, QIHeuristics
from shadowlink.qi_analyser.overlap import find_shared_attributes


def find_candidate_qis(
    profiles: Sequence[DatasetProfile],
    heuristics: QIHeuristics = QIHeuristics(),
) -> list[QICandidate]:
    """Identify candidate quasi-identifiers from dataset profiles using heuristics.

    Parameters
    ----------
    profiles:
        Dataset profiles to examine.
    heuristics:
        Configurable threshold settings.

    Returns
    -------
    list[QICandidate]
    """
    candidates: list[QICandidate] = []
    threshold = heuristics.high_uniqueness_threshold

    # Find shared attributes across datasets if multiple profiles are provided
    shared_canonical: set[str] = set()
    if heuristics.include_shared and len(profiles) > 1:
        shared_map = find_shared_attributes(profiles)
        shared_canonical = set(shared_map.keys())

    for prof in profiles:
        for col in prof.columns:
            # Exclude constant and all-null columns (no distinguishing signal)
            if col.is_constant or col.is_all_null:
                continue

            reasons: list[str] = []
            canonical = normalize_column_name(col.name)

            # Heuristic 1: High uniqueness ratio
            if col.uniqueness_ratio is not None and col.uniqueness_ratio >= threshold:
                reasons.append(
                    f"uniqueness ratio {col.uniqueness_ratio:.2f} >= {threshold:.2f}"
                )

            # Heuristic 2: Shared attribute across datasets
            if heuristics.include_shared and canonical in shared_canonical:
                reasons.append("shared across multiple datasets")

            if reasons:
                candidates.append(
                    QICandidate(
                        column_name=col.name,
                        dataset_name=prof.dataset_name,
                        uniqueness_ratio=col.uniqueness_ratio,
                        reasons=reasons,
                        status="suggested",
                    )
                )

    return candidates


@dataclass(frozen=True)
class QISelection:
    """Immutable management of selected quasi-identifiers."""

    candidates: list[QICandidate]

    def confirm(self, column_name: str, dataset_name: str | None = None) -> QISelection:
        """Mark a candidate as confirmed."""
        updated: list[QICandidate] = []
        for c in self.candidates:
            match_col = c.column_name == column_name
            match_ds = (dataset_name is None) or (c.dataset_name == dataset_name)
            if match_col and match_ds:
                updated.append(
                    QICandidate(
                        column_name=c.column_name,
                        dataset_name=c.dataset_name,
                        uniqueness_ratio=c.uniqueness_ratio,
                        reasons=c.reasons,
                        status="confirmed",
                    )
                )
            else:
                updated.append(c)
        return QISelection(candidates=updated)

    def reject(self, column_name: str, dataset_name: str | None = None) -> QISelection:
        """Mark a candidate as rejected."""
        updated: list[QICandidate] = []
        for c in self.candidates:
            match_col = c.column_name == column_name
            match_ds = (dataset_name is None) or (c.dataset_name == dataset_name)
            if match_col and match_ds:
                updated.append(
                    QICandidate(
                        column_name=c.column_name,
                        dataset_name=c.dataset_name,
                        uniqueness_ratio=c.uniqueness_ratio,
                        reasons=c.reasons,
                        status="rejected",
                    )
                )
            else:
                updated.append(c)
        return QISelection(candidates=updated)

    def add_manual(self, column_name: str, dataset_name: str) -> QISelection:
        """Manually add an attribute as a confirmed quasi-identifier."""
        new_cand = QICandidate(
            column_name=column_name,
            dataset_name=dataset_name,
            uniqueness_ratio=None,
            reasons=["manually added by user"],
            status="confirmed",
        )
        # Avoid duplicate additions
        filtered = [
            c
            for c in self.candidates
            if not (c.column_name == column_name and c.dataset_name == dataset_name)
        ]
        return QISelection(candidates=filtered + [new_cand])

    def selected_columns(self, dataset_name: str | None = None) -> list[str]:
        """Return list of confirmed quasi-identifier column names."""
        selected: list[str] = []
        for c in self.candidates:
            if c.status == "confirmed":
                if dataset_name is None or c.dataset_name == dataset_name:
                    selected.append(c.column_name)
        return selected
