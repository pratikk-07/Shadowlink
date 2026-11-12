# SHADOWLINK Part 2 Benchmark Results

This document contains empirical execution results for the Synthetic Data Generator, Linkage Engine, Attacker Simulator, and Mitigation Evaluator. All figures are generated from deterministic executions of the Shadowlink platform.

---

## 1. Table 5: Attacker Progression Under Progressive Disclosure

Evaluates re-identification risk on the wide demographic & behavioural dataset $W$ ($N=500$, seed=42) across four sequential disclosure steps:
1. Demographic Base QI: `(age, city)`
2. Academic Domain Attribute: `+course`
3. Behavioral Spatial Attribute: `+location`
4. High-Resolution Temporal Attribute: `+timestamp`

### Benchmark Execution Table

| Step | Attributes Disclosed | Mean Candidate Size ($\bar{c}$) | Mean Candidate Risk ($\bar{R}$) | Proportion Unique ($c=1$) | Expected Success Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Step 1** | Age, City | 5.5800 | 0.2130 | 0.0100 (1%) | 0.2130 (21.3%) |
| **Step 2** | +Course | 1.8000 | 0.6933 | 0.4500 (45%) | 0.6933 (69.3%) |
| **Step 3** | +Location | 1.1000 | 0.9533 | 0.9100 (91%) | 0.9533 (95.3%) |
| **Step 4** | +Timestamp | 1.0000 | 1.0000 | 1.0000 (100%) | 1.0000 (100.0%) |

### Observations
- In **Step 1**, disclosing only age and city leaves an average candidate set size of $\approx 5.58$ records; only 1% of entities are uniquely identified.
- Disclosing academic program (**Step 2**) dramatically increases the unique proportion to 45% and candidate risk to 0.6933.
- Adding spatial location (**Step 3**) isolates 91% of individuals into unique equivalence classes ($c=1$).
- Full disclosure including timestamp (**Step 4**) achieves complete unique re-identification (100% uniqueness, candidate set size exactly 1.0).

---

## 2. Table 6: Linkage Methods Benchmark

Evaluates record linkage between Dataset A ($N=385$) and Dataset B ($N=365$) generated via `report_abc(N=500, shared_fraction=0.5, seed=42)`. Ground truth contains $250$ shared entity pairs.
- Blocking key: `city` (reduces $385 \times 365 = 140,525$ naive comparisons down to $12,312$ candidate pairs, reduction ratio $0.8893$).
- Fellegi-Sunter parameters calibrated from ground truth with Laplace smoothing ($s=1.0$).

### Benchmark Execution Table

| Method | Candidates | Matches Predicted | True Positives | Precision | Recall | F1 Score | Reduction Ratio | Runtime (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Deterministic (Exact)** | 12,312 | 1,029 | 209 | 0.2031 | 0.8360 | 0.3268 | 0.8893 | 1.2194 |
| **Similarity (Jaro-Winkler)** | 12,312 | 1,643 | 217 | 0.1321 | 0.8680 | 0.2293 | 0.8893 | 1.2805 |
| **Fellegi-Sunter** | 12,312 | 1,029 | 209 | 0.2031 | 0.8360 | 0.3268 | 0.8893 | 1.3039 |

### Observations
- **Blocking Efficiency**: Standard single-pass blocking on `city` eliminated $88.93\%$ of the comparison space while retaining the candidate matches.
- **Noise Resilience**: The synthetic generator injected $5\%$ typographical noise. Exact deterministic linkage attained recall of $83.60\%$. Jaro-Winkler approximate string matching (threshold $0.85$) successfully bridged typographical distortions, recovering 8 additional true positive matches ($86.80\%$ recall).

---

## 3. Table 7: Mitigation Privacy-Utility Tradeoffs

Evaluates the impact of privacy transformations applied to Dataset A and B ($N=500$, seed=42) against baseline risk and linkage accuracy.

### Benchmark Execution Table

| Condition | Max Class Risk | Mean Class Risk | Uniqueness ($k=1$) | Linkage Precision | Linkage Recall | Linkage F1 | Utility Loss |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Baseline (Unmitigated)** | 1.0000 | 0.3234 | 0.0509 (5.09%) | 0.2024 | 1.0000 | 0.3367 | 0.0000 |
| **2. Age Generalisation (5y)** | 0.5000 | 0.0898 | 0.0000 (0.00%) | 0.0564 | 1.0000 | 0.1067 | 0.2223 |
| **3. Timestamp Coarsening** | 1.0000 | 0.3234 | 0.0509 (5.09%) | 0.2024 | 1.0000 | 0.3367 | 0.1110 |
| **4. Rare City Suppression** | 1.0000 | 0.3234 | 0.0509 (5.09%) | 0.2024 | 1.0000 | 0.3367 | 0.0000 |
| **5. Combined Mitigation** | 0.5000 | 0.0898 | 0.0000 (0.00%) | 0.0564 | 1.0000 | 0.1067 | 0.3332 |

### Observations
- **K-Anonymity & Uniqueness**: 5-year age generalization completely eliminated all unique equivalence classes ($k=1$ dropped from $5.09\%$ to $0.00\%$), capping maximum risk at $0.5000$ ($k \ge 2$).
- **Utility Tradeoff**: The privacy protection lowers Linkage F1 from $0.3367$ to $0.1067$ due to the creation of larger equivalence classes, requiring an attacker to tolerate substantial ambiguity.

