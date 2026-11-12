"""Attacker Simulator: Progressive attribute disclosure and candidate set narrowing."""

from __future__ import annotations

import datetime
from typing import Mapping

import numpy as np
import pandas as pd

from shadowlink.attacker.models import (
    AttackerProfile,
    AttackResult,
    KnowledgeSpec,
    StepMetricReport,
)
from shadowlink.common.exceptions import ValidationError
from shadowlink.common.validation import validate_no_forbidden_columns
from shadowlink.risk.metrics import calculate_candidate_risk


def _is_missing(val: object) -> bool:
    """Safely check if an attribute value is missing/null."""
    if val is None:
        return True
    try:
        return bool(pd.isna(val))  # type: ignore[call-overload,arg-type]
    except Exception:
        return False


def _matches_attribute(
    candidate_val: object,
    target_val: object,
    spec: KnowledgeSpec,
) -> bool:
    """Evaluate whether candidate attribute value satisfies attacker knowledge."""
    if _is_missing(candidate_val):
        return False
    if _is_missing(target_val):
        return True

    if spec.kind == "exact":
        if isinstance(target_val, str) or isinstance(candidate_val, str):
            return str(candidate_val).strip().lower() == str(target_val).strip().lower()
        return bool(candidate_val == target_val)

    if spec.kind == "numeric_tolerance":
        try:
            c_num = float(candidate_val)  # type: ignore[arg-type]
            t_num = float(target_val)  # type: ignore[arg-type]
            return abs(c_num - t_num) <= spec.tolerance
        except (ValueError, TypeError):
            return False

    if spec.kind == "time_window":
        try:
            c_dt = (
                candidate_val
                if isinstance(candidate_val, datetime.datetime)
                else datetime.datetime.fromisoformat(str(candidate_val))
            )
            t_dt = (
                target_val
                if isinstance(target_val, datetime.datetime)
                else datetime.datetime.fromisoformat(str(target_val))
            )
            diff_secs = abs((c_dt - t_dt).total_seconds())
            return diff_secs <= spec.window_minutes * 60
        except (ValueError, TypeError):
            return False

    return False


def simulate_attack(
    df: pd.DataFrame,
    profile: AttackerProfile,
    n_targets: int,
    seed: int,
    knowledge: Mapping[str, KnowledgeSpec] | None = None,
) -> AttackResult:
    """Simulate prosecutor re-identification attack through progressive disclosures.

    Parameters
    ----------
    df:
        Input tabular dataset.
    profile:
        Attacker profile specifying sequence of disclosed attributes.
    n_targets:
        Number of targets to sample from the dataset.
    seed:
        Seed for target sampling and empirical success resolution.
    knowledge:
        Optional per-attribute matching criteria. Defaults to exact.
    """
    validate_no_forbidden_columns(df)
    n = len(df)
    if n == 0:
        raise ValidationError("Input DataFrame cannot be empty.")
    if n_targets <= 0:
        raise ValidationError(f"n_targets must be > 0, got {n_targets}.")

    # Validate that all profile attributes exist in df
    all_profile_attrs = [attr for step in profile.steps for attr in step]
    for attr in all_profile_attrs:
        if attr not in df.columns:
            raise ValidationError(
                f"Attribute '{attr}' in profile '{profile.name}' "
                "not found in DataFrame."
            )

    rng = np.random.default_rng(seed)
    specs: Mapping[str, KnowledgeSpec] = knowledge or {}

    # Sample targets without replacement (or all records if n_targets >= n)
    if n_targets >= n:
        target_indices = list(range(n))
    else:
        target_indices = sorted(rng.choice(n, size=n_targets, replace=False).tolist())

    num_targets = len(target_indices)

    # Initial state: C_0 = all records (0..n-1) for every target
    current_candidates: list[list[int]] = [list(range(n)) for _ in range(num_targets)]
    cumulative_attributes: list[str] = []
    step_reports: list[StepMetricReport] = []
    target_sizes_by_step: dict[int, list[int]] = {}

    # Track candidate sizes per target to feed calculate_candidate_risk
    sizes_history: list[list[int]] = [[n] for _ in range(num_targets)]

    for step_idx, step_attrs in enumerate(profile.steps):
        step_attr_list = list(step_attrs)
        cumulative_attributes.extend(step_attr_list)
        skipped_count = 0

        # Narrow candidate sets for each target
        for t_idx, target_row_idx in enumerate(target_indices):
            candidates = current_candidates[t_idx]

            for attr in step_attr_list:
                target_val = df[attr].iloc[target_row_idx]

                # If target value is missing, skip attribute disclosure for this target
                if _is_missing(target_val):
                    skipped_count += 1
                    continue

                attr_spec = specs.get(attr, KnowledgeSpec(kind="exact"))
                new_c: list[int] = []
                for cand_idx in candidates:
                    cand_val = df[attr].iloc[cand_idx]
                    if _matches_attribute(cand_val, target_val, attr_spec):
                        new_c.append(cand_idx)
                candidates = new_c

            # Invariant: target must remain in candidates under prosecutor model
            if target_row_idx not in candidates:
                candidates.append(target_row_idx)

            # Invariant: candidates must be non-increasing
            prev_len = len(current_candidates[t_idx])
            if len(candidates) > prev_len:
                candidates = current_candidates[t_idx]

            current_candidates[t_idx] = candidates
            sizes_history[t_idx].append(len(candidates))

        current_sizes = [len(c) for c in current_candidates]
        target_sizes_by_step[step_idx] = current_sizes

        # Risk and candidate reduction per target using risk.calculate_candidate_risk
        risks: list[float] = []
        reductions: list[float] = []
        simulated_successes: list[int] = []

        for t_idx, target_row_idx in enumerate(target_indices):
            c_set = current_candidates[t_idx]
            cand_report = calculate_candidate_risk(
                sizes_history[t_idx], initial_count=n
            )
            step_risk = cand_report.steps[-1]
            if step_risk.risk is not None:
                risks.append(step_risk.risk)
            reductions.append(step_risk.candidate_reduction)

            # Empirical simulation: random pick among candidates
            chosen_cand = rng.choice(c_set)
            simulated_successes.append(1 if chosen_cand == target_row_idx else 0)

        mean_candidates = float(np.mean(current_sizes))
        median_candidates = float(np.median(current_sizes))
        min_candidates = int(np.min(current_sizes))
        max_candidates = int(np.max(current_sizes))
        mean_risk = float(np.mean(risks)) if risks else 0.0
        mean_reduction = float(np.mean(reductions))
        unique_fraction = float(sum(1 for s in current_sizes if s == 1) / num_targets)

        # Expected success rate = mean(1/|C|) = mean risk (by definition)
        expected_success_rate = mean_risk
        simulated_success_rate = float(np.mean(simulated_successes))

        step_reports.append(
            StepMetricReport(
                step=step_idx + 1,
                attributes=step_attr_list,
                cumulative_attributes=list(cumulative_attributes),
                mean_candidates=mean_candidates,
                median_candidates=median_candidates,
                min_candidates=min_candidates,
                max_candidates=max_candidates,
                mean_risk=mean_risk,
                mean_reduction=mean_reduction,
                unique_fraction=unique_fraction,
                expected_success_rate=expected_success_rate,
                simulated_success_rate=simulated_success_rate,
                skipped_attributes_count=skipped_count,
            )
        )

    return AttackResult(
        profile_name=profile.name,
        target_count=num_targets,
        total_records=n,
        step_reports=step_reports,
        candidate_sizes_per_target=target_sizes_by_step,
    )
