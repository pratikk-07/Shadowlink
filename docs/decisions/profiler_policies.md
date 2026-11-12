# Decision: Data Profiler Metrics Policies

**Status**: Accepted  
**Phase**: 1 (Data Profiler)

## Context

A clear, unambiguous definition is required for all data profiling metrics:
`missing_rate`, `distinct_count`, `uniqueness_ratio`, and duplicate rows.

## Decisions

### 1. `missing_rate`
- **Formula**: `missing_count / total_rows`
- **Zero-row behavior**: When `total_rows == 0`, `missing_rate` is `None` (representing an undefined rate, not 0.0).

### 2. `distinct_count`
- **Policy**: Missing values are **NOT** counted as distinct values.
- Only non-missing (valid data) values are evaluated for distinctness: `series.dropna().nunique()`.

### 3. `uniqueness_ratio`
- **Formula**: `distinct_non_missing_count / total_rows`
- **Zero-row behavior**: When `total_rows == 0`, `uniqueness_ratio` is `None`.
- **Note**: The denominator is total rows, not non-missing rows.

### 4. `is_constant` and `is_all_null`
- `is_constant` is `True` if and only if `distinct_count == 1` and `missing_count == 0` (all rows carry the exact same non-null value).
- `is_all_null` is `True` if `missing_count == total_rows` and `total_rows > 0`.

### 5. Duplicate Row Policy
- Count of duplicate rows is evaluated using `df.duplicated(keep="first").sum()`.
- The first occurrence is preserved; subsequent occurrences are counted as duplicates.
- Missing values compare equal (`NaN == NaN`).

