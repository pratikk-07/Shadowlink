# Decision: Worst-Case Attacker Assumption in Mitigation Evaluation

**Status**: Accepted  
**Phase**: 6 (Mitigation Evaluator)

## Context

When mitigating privacy risks through generalization (e.g. 5-year age bands) or coarsening (e.g. timestamp truncated to date), an attacker attempting to link external auxiliary records might also possess or adapt their knowledge to the mitigated representation.

## Decision

1. **Worst-Case Kerckhoffs Assumption**: We assume an attacker knows the exact mitigation rules and algorithms applied to the released data.
2. **Harmonized Representation**: When evaluating mitigated linkage and re-identification risk, the attacker's auxiliary attributes undergo the identical transformation (e.g. matching `'20-24'` against `'20-24'`).
3. **Defense Against Ambiguity**: Mitigation success is measured by the enlargement of equivalence classes ($k$-anonymity) and the elimination of unique records ($k=1$), rather than relying on syntactic format mismatches.

## Consequences

- Privacy protection is evaluated robustly against sophisticated adversaries.
- Prevents false confidence where a trivial format conversion would break security.

