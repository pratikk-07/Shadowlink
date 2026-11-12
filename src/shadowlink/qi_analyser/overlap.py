"""Shared attribute discovery and cross-dataset overlap indicators."""

from __future__ import annotations

from typing import Sequence

from shadowlink.common.exceptions import ValidationError
from shadowlink.common.normalization import normalize_column_name
from shadowlink.profiler.models import DatasetProfile
from shadowlink.qi_analyser.models import (
    OverlapReport,
    PairwiseOverlap,
    SharedAttributeEntry,
    SharedAttributeMap,
)


def find_shared_attributes(
    profiles: Sequence[DatasetProfile],
) -> SharedAttributeMap:
    """Discover attributes shared across two or more datasets using canonical names.

    Parameters
    ----------
    profiles:
        List of DatasetProfile objects to inspect.

    Returns
    -------
    SharedAttributeMap
        Mapping from canonical name to occurrences across datasets.
    """
    raw_map: dict[str, list[SharedAttributeEntry]] = {}

    for prof in profiles:
        dataset_name = prof.dataset_name
        seen_canonical: dict[str, str] = {}

        for col in prof.columns:
            canonical = normalize_column_name(col.name)
            if not canonical:
                continue

            if canonical in seen_canonical:
                prev_orig = seen_canonical[canonical]
                raise ValidationError(
                    f"Dataset '{dataset_name}' contains multiple columns that "
                    f"normalize to the same canonical name '{canonical}': "
                    f"'{prev_orig}' and '{col.name}'."
                )
            seen_canonical[canonical] = col.name

            entry = SharedAttributeEntry(
                dataset_name=dataset_name,
                original_name=col.name,
                kind=col.kind,
                dtype_compatible=True,
            )
            raw_map.setdefault(canonical, []).append(entry)

    # Filter to only attributes shared across at least 2 distinct datasets
    shared_map: SharedAttributeMap = {}
    for canonical, entries in raw_map.items():
        distinct_datasets = {e.dataset_name for e in entries}
        if len(distinct_datasets) >= 2:
            # Check type compatibility across datasets
            kinds = {e.kind for e in entries}
            is_compatible = len(kinds) == 1
            # Reconstruct entries with accurate dtype_compatible flag
            updated_entries = [
                SharedAttributeEntry(
                    dataset_name=e.dataset_name,
                    original_name=e.original_name,
                    kind=e.kind,
                    dtype_compatible=is_compatible,
                )
                for e in entries
            ]
            shared_map[canonical] = updated_entries

    return shared_map


def calculate_overlap_indicators(
    shared_map: SharedAttributeMap,
    profiles: Sequence[DatasetProfile],
) -> OverlapReport:
    """Calculate pairwise attribute overlap counts and fractions between datasets.

    Parameters
    ----------
    shared_map:
        Computed SharedAttributeMap.
    profiles:
        List of DatasetProfile instances.

    Returns
    -------
    OverlapReport
    """
    # Map dataset_name to its column count
    col_counts = {p.dataset_name: p.column_count for p in profiles}
    dataset_names = sorted(col_counts.keys())

    pairs: list[PairwiseOverlap] = []
    n = len(dataset_names)

    for i in range(n):
        for j in range(i + 1, n):
            ds_a = dataset_names[i]
            ds_b = dataset_names[j]

            # Count shared attributes between ds_a and ds_b
            shared_count = 0
            for entries in shared_map.values():
                dsets_in_entry = {e.dataset_name for e in entries}
                if ds_a in dsets_in_entry and ds_b in dsets_in_entry:
                    shared_count += 1

            total_a = col_counts[ds_a]
            total_b = col_counts[ds_b]

            frac_a = (shared_count / total_a) if total_a > 0 else 0.0
            frac_b = (shared_count / total_b) if total_b > 0 else 0.0

            pairs.append(
                PairwiseOverlap(
                    dataset_a=ds_a,
                    dataset_b=ds_b,
                    shared_column_count=shared_count,
                    fraction_of_a=frac_a,
                    fraction_of_b=frac_b,
                )
            )

    return OverlapReport(pairs=pairs)

