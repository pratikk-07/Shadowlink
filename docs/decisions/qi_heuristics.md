# Decision: QI Heuristics — Uniqueness Threshold

**Status**: Accepted  
**Phase**: 4 (QI Analyser)

## Context

Deciding which columns are quasi-identifiers (QIs) requires heuristics.
There is no universally agreed scientific threshold.

## Decision

Default heuristics (`QIHeuristics`):

| Heuristic | Default value | Meaning |
|-----------|--------------|---------|
| `high_uniqueness_threshold` | **0.5 (inclusive)** | Flag column if `uniqueness_ratio >= threshold` |
| Shared across datasets | — | Also flag column if it appears in ≥ 1 other dataset profile |
| Constant or all-null columns | — | Never flagged (no discriminating power) |

A column is flagged (`status="suggested"`) if **either** condition holds.
Every `QICandidate` carries a `reasons` list explaining which conditions triggered.

## Important Caveat

> This threshold is a **configurable heuristic default**, NOT a scientifically
> validated threshold.  It was chosen to flag columns that could differentiate
> more than half the records.  Domain experts should review suggestions and
> confirm/reject via `QISelection.confirm()` / `QISelection.reject()`.

## Worked Example (Fixtures A + B)

| Column  | uniqueness_ratio | >= 0.5? | Shared with B? | Flagged? |
|---------|-----------------|---------|----------------|----------|
| age     | 0.5             | ✓       | ✓ (` Age `)   | **yes**  |
| city    | 0.375           | ✗       | ✓ (`CITY`)    | **yes**  |
| course  | 0.25            | ✗       | ✗             | no       |

