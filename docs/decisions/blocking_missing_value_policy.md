# Decision: Blocking Key Missing Value Policy

**Status**: Accepted  
**Phase**: 3 (Linkage Blocking)

## Context

Candidate pair blocking groups records by shared attribute keys (e.g. `city`, `course`) to avoid evaluating all $N_A \times N_B$ pairs. Real-world and synthetic datasets inevitably contain missing or null values in blocking columns.

## Decision

1. **Strict Key Exclusion**: If any attribute component of a blocking pass is missing (`None`, `NaN`, empty string), the record is excluded from that specific blocking pass.
2. **Multi-Pass Redundancy**: Multi-pass blocking (disjunctive union of candidate sets across different passes) guarantees that records missing a key in pass 1 can still be linked via pass 2 (e.g. blocking on `course` if `city` is missing).
3. **No Synthetic Null Buckets**: Null values are never placed in a shared `"NULL"` bucket, as doing so would cause quadratic blowup and false-positive flooding among incomplete records.

## Consequences

- High reduction ratios are preserved without polluting candidate sets with uninformative matches.
- Callers requiring complete coverage over noisy attributes must configure multiple complementary blocking passes.

