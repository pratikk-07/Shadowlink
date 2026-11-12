# Decision: Tie-Adjusted Re-Identification Success Metrics

**Status**: Accepted  
**Phase**: 2 (Attacker Simulator) & Phase 5 (Evaluator)

## Context

When an attacker isolates a target individual into a candidate set of size $c > 1$, all candidates in the equivalence class match the attacker's auxiliary knowledge equally well. An evaluation framework must determine how to score attack success when exact uniqueness ($c = 1$) is not attained.

## Decision

1. **Dual Metric Reporting**: Never report a single composite score. Always report two complementary re-identification success metrics:
   - **Tie-Adjusted Success Rate**: Expected probability of correct match under uniform random selection from the top-scoring candidate set: $\text{Credit} = \frac{1}{c}$ if the true record is in the candidate set, else $0$.
   - **Deterministic Success Rate**: Empirical success when breaking ties by selecting the candidate with the lexicographically smallest `record_id`.
2. **Monotonicity Consistency**: As auxiliary attributes are progressively revealed, candidate set sizes must monotonically decrease or remain constant ($c_{t+1} \le c_t$), and candidate risk must monotonically increase or remain constant ($R_{t+1} \ge R_t$).

## Consequences

- Accurately captures privacy risk in ambiguous equivalence classes without overly optimistic or pessimistic assumptions.
- Matches theoretical class risk definitions ($1/|E_i|$) under prosecutor threat models.

