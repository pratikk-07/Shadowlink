# Decision: Risk Metric Assumptions

**Status**: Accepted  
**Phase**: 3 (Risk Engine)

## Context

Re-identification risk can be modelled under different attacker assumptions.
SHADOWLINK adopts the **prosecutor model**.

## Decision

**All class-based risk metrics in SHADOWLINK assume the prosecutor model:**

> The attacker *knows* the target individual is in the dataset and searches
> for them by matching quasi-identifier values.

Under this model, the probability that an attacker correctly re-identifies
a record from an equivalence class of size *f* is **1/f**.

## Metrics Produced (no composite score)

Each metric is reported separately with its own formula, denominator, and assumption.

| Metric | Formula | Denominator | Source module |
|--------|---------|-------------|---------------|
| `k` | min class size | — | `qi_analyser.equivalence` |
| `max_class_risk` | 1/k | k | `risk.metrics` |
| `average_class_risk` | num_classes / records_analysed | records_analysed | `risk.metrics` |
| `uniqueness` | singleton_records / records_analysed | records_analysed | `risk.metrics` |
| `per_record_risk` | 1/f for each record | class size f | `risk.metrics` |

**R3 compliance**: There is no combined/overall/total/composite risk score.

## Limitations

- k-anonymity does not protect against attribute inference or background
  knowledge attacks.
- These metrics are computed on the released dataset, not on the population.
- The prosecutor model is conservative; the journalist model is more lenient.

