# Decision: Missing Value Policy in Equivalence Classes

**Status**: Accepted  
**Phase**: 2 (Equivalence Classes)

## Context

A record may have a missing value (`NaN`) in one or more quasi-identifier
columns.  Two policy choices arise:
1. Treat missing as its own group value ("missing is unique").
2. Exclude records that have any missing QI from the analysis.

## Decision

`missing_policy` is a caller-supplied parameter with two valid values:

| Value              | Behaviour |
|--------------------|-----------|
| `"own_group"`      | Missing is treated as a distinct group value, never equal to any real value or to another missing cell. Each unique combination of (non-missing values, missing positions) forms its own class. |
| `"exclude_records"`| Any record with at least one missing QI is excluded before grouping. `excluded_record_count` records this count. Denominators use `records_analysed = total - excluded`. |

Default: `"own_group"`.

## Consequences

- `"own_group"` preserves all records but may inflate singleton counts.
- `"exclude_records"` reduces n but avoids treating missing as a signal.
- Callers must document which policy they applied when reporting results.

