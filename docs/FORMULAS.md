# FORMULAS — All Metrics with Worked Examples on Fixture A

> **Important**: Every number in this document was produced by a real run on
> `tests/fixtures/tiny_people_a.csv`.  See `docs/RESULTS_FROM_FIXTURES.md`
> for the exact CLI commands and their outputs.

---

## 1. Profiler Metrics

### 1.1 missing_rate

```
missing_rate = missing_count / row_count
```

- **Denominator**: total rows (including missing rows).
- **Edge case**: `row_count == 0` → `None` (undefined, not zero).
- **Fixture A**: all columns have `missing_count = 0`, so `missing_rate = 0.0`.

### 1.2 uniqueness_ratio

```
uniqueness_ratio = distinct_non_missing_count / row_count
```

- **Denominator**: total rows (not just non-missing rows).
- **Edge case**: `row_count == 0` → `None`.
- **distinct_count** counts distinct *non-missing* values only.
- **Fixture A**:
  - `age`: 4 distinct / 8 rows = **0.5**
  - `city`: 3 distinct / 8 rows = **0.375**
  - `course`: 2 distinct / 8 rows = **0.25**

### 1.3 duplicate_row_count

```
duplicate_row_count = df.duplicated(keep="first").sum()
```

- **Policy**: `keep="first"` — the first occurrence is *not* a duplicate; every
  subsequent identical row is counted.
- **NaN handling**: pandas treats NaN as equal to NaN in `duplicated()`.
- **Fixture A**: rows 5 and 6 are both `22,Delhi,CSE`.  Row 5 is kept;
  row 6 is counted → `duplicate_row_count = 1`.

---

## 2. Equivalence-Class Metrics

Let *n* = `records_analysed`, *C₁ … Cₖ* be the equivalence classes,
and *fᵢ* = `|Cᵢ|` (class size).

### 2.1 k-anonymity (k)

```
k = min(f₁, f₂, …, fₘ)
```

- **Assumption**: each class member is indistinguishable from the others on the QI columns.
- **Fixture A, QI=[age,city]**: sizes {2,1,2,2,1} → **k = 1**.
- **Fixture A, QI=[age,city,course]**: sizes {1,1,1,1,1,2,1} → **k = 1**.

### 2.2 Discernibility Metric (DM)

```
DM = Σᵢ fᵢ²
```

- **Interpretation**: larger DM = worse utility (more records "blurred" into large groups).
  A perfectly unique dataset (all singletons) has DM = n.
- **Fixture A, QI=[age,city]**: 4+1+4+4+1 = **14**.
- **Fixture A, QI=[age,city,course]**: 1+1+1+1+1+4+1 = **10**.

---

## 3. Risk Engine Metrics (Prosecutor Model)

**Assumption (all metrics)**: The prosecutor model — the attacker *knows* the
target individual is in the dataset and searches for them by quasi-identifier
match.

### 3.1 max_class_risk

```
max_class_risk = 1 / k
```

- **Denominator**: k (minimum class size).
- **Fixture A, QI=[age,city]**: 1/1 = **1.0**.

### 3.2 average_class_risk

```
average_class_risk = num_classes / records_analysed
```

Equivalently, this is the mean of per-record risks `(1/fᵢ)`:

```
average_class_risk = (1/n) × Σᵢ fᵢ × (1/fᵢ) = num_classes / n
```

- **Fixture A, QI=[age,city]**: 5/8 = **0.625**.
- **Fixture A, QI=[age,city,course]**: 7/8 = **0.875**.

### 3.3 uniqueness (singleton_record_proportion)

```
uniqueness = singleton_record_count / records_analysed
```

- **Singleton record**: a record whose equivalence class has size 1.
- **Fixture A, QI=[age,city]**: 2/8 = **0.25**.

### 3.4 per_record_risk (Series)

```
per_record_risk[i] = 1 / f(i)
```

where `f(i)` is the size of the equivalence class containing record `i`.

---

## 4. Mitigation Examples

### 4.1 generalize_age (width=5, base=0)

Bin formula:  `lo = base + floor((age - base) / width) × width`
              `hi = lo + width - 1`
              label = `"lo-hi"`

| age | lo | hi | label   |
|-----|----|----|---------|
| 20  | 20 | 24 | "20-24" |
| 21  | 20 | 24 | "20-24" |
| 22  | 20 | 24 | "20-24" |
| 23  | 20 | 24 | "20-24" |

After generalization, QI=[age_bin, city]:  sizes {3,4,1}, DM=**26**, k=**1**.

### 4.2 suppress_small_classes (k=2) on generalized frame

Remove all classes with size < 2.  Only (20-24, Mumbai) has size 1 → remove
the 1 Mumbai record.  Remaining: N=7, {Kolkata:3, Delhi:4}.

- k = **3**, DM = **25**, average_risk = 2/7, records_suppressed = **1**.

### 4.3 suppress_rare_values (city, min_freq=2) on original

City counts: Kolkata=3, Delhi=4, Mumbai=1.  Mumbai < 2 → replace with "SUPPRESSED".
cells_changed = **1**.

