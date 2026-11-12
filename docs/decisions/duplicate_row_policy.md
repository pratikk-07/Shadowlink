# Decision: Duplicate Row Policy

**Status**: Accepted  
**Phase**: 1 (Data Profiler)

## Context

A row is a "duplicate" if every column value is identical to another row.
pandas `DataFrame.duplicated()` has a `keep` parameter that controls which
occurrence is counted.

## Decision

`duplicate_row_count = df.duplicated(keep="first").sum()`

- `keep="first"` → the first occurrence is **not** marked as a duplicate.
  Only subsequent repeated rows are counted.
- NaN values: pandas treats `NaN == NaN` as `True` inside `duplicated()`.

## Worked Example (Fixture A)

Rows 5 and 6 are both `22,Delhi,CSE`.

| row | keep="first" duplicated? |
|-----|--------------------------|
| 5   | False (first occurrence) |
| 6   | True  (counted)          |

`duplicate_row_count = 1`

## Consequences

- The duplicate count is **informational**, not a correctness signal.
  Some use cases intentionally have duplicates (repeated measurements).
- Callers who want to deduplicate should do so before calling SHADOWLINK,
  or accept that two identical quasi-identifier records form a valid class of size 2.

