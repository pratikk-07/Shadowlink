# Architecture — SHADOWLINK Platform

## 1. Overview & End-to-End Pipeline Data Flow (Figure 1)

SHADOWLINK connects all components into a modular, defensive privacy-engineering and record-linkage platform. Data flows strictly forward through pure functions without in-place mutation of DataFrames.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SHADOWLINK PIPELINE                             │
└────────────────────────────────────────────────────────────────────────┘

  [1. Synthetic Generator] (Latent population + noise injection)
             │
             ├──────────────────────────────────────────────┐ (Isolate Ground Truth)
             │ Datasets (A, B, C)                           │
             ▼                                              ▼
  [2. Data Profiler] (Profiles, distributions, null rates)  │
             │                                              │
             ▼                                              │
  [3. QI Analyser] (Candidate QIs & shared attributes)      │
             │                                              │
             ▼                                              │
  [4. Risk Engine] (Equivalence classes, class-based risk)  │
             │                                              │
             ▼                                              │
  [5. Attacker Simulator] (Progressive attribute narrowing) │
             │                                              │
             ▼                                              │
  [6. Linkage Engine] (Blocking, Deterministic, Sim, FS)    │
             │                                              │
             ▼                                              │
  [7. Mitigation Engine] (Generalization, suppression,      │
                          coarsening, re-run Stages 4-6)    │
             │                                              │
             ▼                                              │
  [8. Evaluator] <──────────────────────────────────────────┘
      (Precision, Recall, F1, Re-id Success, Utility Loss)
             │
             ▼
  [9. Report Writer] (report.json & report.md audit artifacts)
```

---

## 2. Nine-Stage Execution Order

1. **Stage 1 — Synthetic Data Generation**: Latent population sampling with deterministic partitioning of shared ($f \cdot N$) and exclusive entities. Non-id cells receive controlled typographical and missing-value noise. Shuffled opaque record IDs are assigned. Ground truth correspondence is isolated.
2. **Stage 2 — Data Profiling**: Statistical profiling of every generated dataset (row counts, column kinds, distinct counts, null fractions, uniqueness ratios).
3. **Stage 3 — Shared Attributes & Candidate QIs**: Cross-dataset overlap detection and heuristic quasi-identifier identification based on uniqueness thresholds.
4. **Stage 4 — Equivalence Classes & Baseline Risk**: Construction of equivalence classes on configured quasi-identifiers. Calculates $k$-anonymity, max class risk, average class risk, uniqueness proportion, and discernibility metric.
5. **Stage 5 — Attacker Simulator**: Simulation of a prosecutor threat model with progressive attribute disclosure. Asserts non-increasing candidate sets ($C_{j+1} \subseteq C_j$) and computes per-step candidate risk.
6. **Stage 6 — Record Linkage Engine**: Multi-pass candidate pair blocking and comparative scoring using Deterministic (Exact), Weighted Similarity (Jaro-Winkler), and Fellegi-Sunter weight of evidence methods. *Stage 6 operates completely blind to ground truth.*
7. **Stage 7 — Privacy Mitigation**: Applies pure transformations (age binning, timestamp coarsening, rare value suppression). Re-evaluates Stages 4, 5, and 6 on mitigated data to measure risk reduction.
8. **Stage 8 — Evaluation (Ground Truth Authority)**: Evaluates linkage predictions against ground truth entity pairs (Precision, Recall, F1 score). Measures blocking reduction ratio, pairs completeness, tie-adjusted re-identification success, and cell utility loss.
9. **Stage 9 — Unified Audit Reporting**: Compiles all execution metrics into deterministic `report.json` and human-readable `report.md`.

---

## 3. Pipeline JSON Configuration Schema

The end-to-end pipeline is driven by a configuration file passed to `run-pipeline`:

```json
{
  "seed": 42,
  "generator": {
    "preset": "report_abc",
    "population_size": 100,
    "shared_fraction": 0.5,
    "typo_rate": 0.05,
    "missing_rate": 0.02
  },
  "qi_analyser": {
    "target_dataset": "A",
    "qi_columns": ["age", "city"]
  },
  "attacker": {
    "steps": [["age", "city"], ["course"]],
    "n_targets": 25
  },
  "linkage": {
    "left_dataset": "A",
    "right_dataset": "B",
    "blocking_keys": ["city"],
    "attributes": ["age", "city"],
    "threshold": 0.85
  },
  "mitigation": {
    "transformations": [
      {
        "kind": "generalize_age",
        "parameters": {
          "column": "age",
          "bin_width": 5
        }
      }
    ]
  }
}
```

### Schema Specification
- `seed` (*integer*, required): RNG seed for reproducible generation, sampling, and simulation.
- `generator` (*object*):
  - `preset`: `"report_abc"` (Datasets A, B, C) or `"wide_release"` (Dataset W).
  - `population_size`: Total latent population size $N$.
  - `shared_fraction`: Proportion of population appearing across all datasets.
  - `typo_rate`: Single-character edit rate on string attributes.
  - `missing_rate`: Null cell probability.
- `qi_analyser` (*object*):
  - `target_dataset`: Dataset designated for equivalence class and risk analysis.
  - `qi_columns`: Selected quasi-identifier attribute names.
- `attacker` (*object*):
  - `steps`: Ordered list of attribute subsets sequentially revealed by the adversary.
  - `n_targets`: Number of individuals sampled for attack simulation.
- `linkage` (*object*):
  - `left_dataset` / `right_dataset`: Dataset pair to link.
  - `blocking_keys`: Attribute keys defining blocking passes.
  - `attributes`: Attribute names evaluated by linkage comparators.
  - `threshold`: Similarity score threshold for match classification.
- `mitigation` (*object*):
  - `transformations`: Ordered pipeline of transformation specifications (`kind`, `parameters`).

---

## 4. Key Design Decisions & Boundary Enforcement

- `ground_truth_boundary.md`: Rule R2 strictly prohibits `linkage` and `attacker` from importing `evaluator` or accessing ground-truth identifiers.
- `record_id_policy.md`: Record IDs are assigned post-shuffle; row ordering conveys zero latent identity information.
- `blocking_missing_value_policy.md`: Incomplete blocking keys exclude records from that pass without synthetic null buckets.
- `tie_adjusted_reidentification.md`: Evaluates expected re-identification risk ($1/c$) rather than arbitrary tie-break decisions.
- `mitigation_worst_case_attacker.md`: Assumes adversary auxiliary data undergoes identical transformation harmonisation.
- `generator_latent_population.md`: Single latent population partitioned deterministically using the largest remainder method.
