# API Contracts — Platform Integration

> **Status**: [AGREED & IMPLEMENTED]  
> All inter-module interfaces between Profiler, QI Analyser, Risk Engine, Mitigation, Synthetic Data Generator, Linkage Engine, Attacker Simulator, and Evaluator are fully implemented and verified green against test gates.

---

## 1. DatasetProfile (Profiler -> Evaluator)
`shadowlink.profiler.models.DatasetProfile`
```python
{
    "dataset_name": str,
    "row_count": int,
    "column_count": int,
    "duplicate_row_count": int,
    "memory_bytes": int,
    "columns": [
        {
            "name": str,
            "dtype": str,
            "kind": str,  # "numeric" | "categorical" | "datetime" | "boolean"
            "missing_count": int,
            "missing_rate": float | None,
            "distinct_count": int,
            "uniqueness_ratio": float | None,
            "is_constant": bool,
            "is_all_null": bool,
            "has_mixed_types": bool,
        }
    ],
}
```
**Status**: [IMPLEMENTED]. Top frequencies are excluded to prevent categorical value leakage.

---

## 2. EquivalenceClassResult (QI Analyser -> Risk & Mitigation)
`shadowlink.qi_analyser.equivalence.EquivalenceClassResult`
```python
{
    "qi_columns": list[str],
    "total_records": int,
    "records_analysed": int,
    "excluded_record_count": int,
    "class_sizes": list[int],
    "num_classes": int,
    "k": int | None,
    "singleton_class_count": int,
    "singleton_record_count": int,
    "singleton_record_proportion": float | None,
    "missing_policy": str,
}
```
**Status**: [IMPLEMENTED]. Reused across risk calculations and mitigation evaluations.

---

## 3. AttackerStepSummary & StepMetricReport (Attacker -> Risk & CLI)
`shadowlink.common.schemas.AttackerStepSummary`
```python
{
    "step": int,
    "known_attributes": list[str],
    "candidate_count": int,
}
```
`shadowlink.attacker.models.StepMetricReport`
```python
{
    "step": int,
    "attributes": list[str],
    "cumulative_attributes": list[str],
    "mean_candidates": float,
    "median_candidates": float,
    "min_candidates": int,
    "max_candidates": int,
    "mean_risk": float,
    "mean_reduction": float,
    "unique_fraction": float,
    "expected_success_rate": float,
    "simulated_success_rate": float,
    "skipped_attributes_count": int,
}
```
**Status**: [IMPLEMENTED]. Integrates directly with `calculate_candidate_risk()` in `shadowlink.risk.metrics`.

---

## 4. Linkage Scored Pairs Output (Linkage Engine -> Evaluator / Export)
Output DataFrame of `deterministic_linkage`, `similarity_linkage`, and `fellegi_sunter_linkage`:
```python
{
    "left_dataset": str,
    "left_id": str,
    "right_dataset": str,
    "right_id": str,
    "score": float,
    "decision": str,  # "match" | "possible" | "non_match"
    "method": str,  # "deterministic" | "similarity" | "fellegi_sunter"
    # per-attribute evidence similarity columns: e.g. "sim_city", "sim_age"
}
```
**Status**: [IMPLEMENTED]. Strict Ground Truth Boundary adhered to: no ground truth or entity ID columns present anywhere.

---

## 5. Ground Truth & Linkage Evaluation (Evaluator)
`shadowlink.evaluator.metrics.LinkageEvaluation`
```python
{
    "true_positives": int,
    "false_positives": int,
    "false_negatives": int,
    "total_predicted_matches": int,
    "total_true_matches": int,
    "precision": float | None,
    "recall": float | None,
    "f1_score": float | None,
}
```
**Status**: [IMPLEMENTED].
