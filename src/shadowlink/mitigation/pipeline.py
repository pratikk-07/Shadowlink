"""Execution pipeline for chaining multiple privacy transformations."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import pandas as pd

from shadowlink.common.exceptions import ConfigError
from shadowlink.mitigation.binning import bin_numeric
from shadowlink.mitigation.generalization import (
    generalize_age,
    generalize_by_hierarchy,
)
from shadowlink.mitigation.models import (
    MitigationReport,
    TransformationLogEntry,
    TransformationSpec,
)
from shadowlink.mitigation.spatial import coarsen_coordinates
from shadowlink.mitigation.suppression import (
    suppress_rare_values,
    suppress_small_classes,
)
from shadowlink.mitigation.temporal import coarsen_timestamp
from shadowlink.mitigation.utility import compare_privacy_utility


def run_mitigation_experiment(
    original: pd.DataFrame,
    specs: Sequence[TransformationSpec],
    qi_columns: Sequence[str],
    queries: Mapping[str, Callable[[pd.DataFrame], Any]] | None = None,
) -> MitigationReport:
    """Execute privacy transformations and measure privacy-utility trade-off.

    Original DataFrame is never modified.
    """
    current_df = original.copy(deep=True)
    logs: list[TransformationLogEntry] = []

    for spec in specs:
        kind = spec.kind
        params = spec.parameters

        if kind == "generalize_age":
            res = generalize_age(current_df, **params)
        elif kind == "generalize_by_hierarchy":
            res = generalize_by_hierarchy(current_df, **params)
        elif kind == "bin_numeric":
            res = bin_numeric(current_df, **params)
        elif kind == "suppress_rare_values":
            res = suppress_rare_values(current_df, **params)
        elif kind == "suppress_small_classes":
            res = suppress_small_classes(current_df, **params)
        elif kind == "coarsen_timestamp":
            res = coarsen_timestamp(current_df, **params)
        elif kind == "coarsen_coordinates":
            res = coarsen_coordinates(current_df, **params)
        else:
            raise ConfigError(
                f"Unknown transformation kind '{kind}' in pipeline specification."
            )

        current_df = res.df
        logs.append(res.log)

    return compare_privacy_utility(
        original=original,
        transformed=current_df,
        qi_columns=qi_columns,
        queries=queries,
        transformation_logs=logs,
    )
