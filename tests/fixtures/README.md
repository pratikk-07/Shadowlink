# Test Fixtures — Hand-Verified Oracle Data

These tiny CSV files are the **golden oracles** for every test assertion in
SHADOWLINK.  Every expected number in the test suite was derived by hand
calculation from these rows and cross-checked before writing any code.

> **Never edit these files** without updating all test assertions and the
> `docs/RESULTS_FROM_FIXTURES.md` document that records real CLI outputs.

---

## `tiny_people_a.csv`

8 rows, 3 columns: `age`, `city`, `course`.

```
age,city,course
20,Kolkata,CSE
20,Kolkata,ECE
21,Kolkata,CSE
21,Delhi,CSE
21,Delhi,ECE
22,Delhi,CSE   ← row index 5
22,Delhi,CSE   ← row index 6  (duplicate of row 5)
23,Mumbai,ECE
```

### Profile expectations (Phase 1)

| Column  | distinct (non-missing) | uniqueness_ratio | missing_count |
|---------|------------------------|------------------|---------------|
| age     | 4 (20,21,22,23)        | 4/8 = **0.5**    | 0             |
| city    | 3 (Kolkata,Delhi,Mumbai)| 3/8 = **0.375** | 0             |
| course  | 2 (CSE,ECE)            | 2/8 = **0.25**   | 0             |

`duplicate_row_count = 1`

Explanation: `df.duplicated(keep="first")` marks row index 6 as a duplicate
of row index 5 (both are `22,Delhi,CSE`).  The count of `True` entries = **1**.
This is documented in `docs/decisions/duplicate_row_policy.md`.

### Equivalence-class expectations (Phase 2)

**QI = [age, city]**

| Class          | Members          | Size |
|----------------|------------------|------|
| (20, Kolkata)  | rows 0,1         | 2    |
| (21, Kolkata)  | row 2            | 1    |
| (21, Delhi)    | rows 3,4         | 2    |
| (22, Delhi)    | rows 5,6         | 2    |
| (23, Mumbai)   | row 7            | 1    |

- num_classes = 5
- k = min(2,1,2,2,1) = **1**
- singleton_record_count = 2  (rows 2 and 7)
- singleton_record_proportion = 2/8 = **0.25**
- max_risk = 1/1 = **1.0**
- average_risk = 5/8 = **0.625**
- DM = 4+1+4+4+1 = **14**

**QI = [age, city, course]**

| Class                   | Size |
|-------------------------|------|
| (20, Kolkata, CSE)      | 1    |
| (20, Kolkata, ECE)      | 1    |
| (21, Kolkata, CSE)      | 1    |
| (21, Delhi, CSE)        | 1    |
| (21, Delhi, ECE)        | 1    |
| (22, Delhi, CSE)        | 2    |
| (23, Mumbai, ECE)       | 1    |

- num_classes = **7**
- k = **1**
- singleton_record_count = 6
- singleton_record_proportion = **0.75**
- average_risk = 7/8
- DM = 1+1+1+1+1+4+1 = **10**

### Mitigation chain expectations (Phase 5)

**Step 1 — generalize_age(width=5, base=0)**

Ages 20,21,22,23 all fall in [20,25) → label "20-24".

QI [age_bin, city]:

| Class            | Size |
|------------------|------|
| (20-24, Kolkata) | 3    |
| (20-24, Delhi)   | 4    |
| (20-24, Mumbai)  | 1    |

- k=1, singleton 1/8, average_risk 3/8, DM = 9+16+1 = **26**

**Step 2 — suppress_small_classes(k=2) on the generalized frame**

Removes the 1 Mumbai record. N=7, classes: Kolkata(3), Delhi(4).

- k = min(3,4) = **3**
- singleton=0, average_risk = 2/7, max_risk = 1/3
- DM = 9+16 = **25**
- records_suppressed = **1** (of original 8)

**suppress_rare_values(column=city, minimum_frequency=2) on original**

City frequencies: Kolkata=3, Delhi=4, Mumbai=1.
Mumbai < 2 → replaced.  cells_changed = **1**.

---

## `tiny_people_b.csv`

5 rows, 4 columns with deliberately messy header names (spaces, mixed case):

| ` Age ` | `CITY`   | `location`      | `timestamp`          |
|---------|----------|-----------------|----------------------|
| 22      | Mumbai   | Bandra          | 2024-01-15 09:30:00  |
| 25      | Delhi    | Connaught Place | 2024-01-16 14:45:00  |
| 21      | Kolkata  | Park Street     | 2024-01-17 11:00:00  |
| 28      | Chennai  | Anna Nagar      | 2024-01-18 16:20:00  |
| 23      | Mumbai   | Juhu            | 2024-01-19 08:15:00  |

After `normalize_column_name`: `age`, `city`, `location`, `timestamp`.

**Shared attributes with Dataset A** (Phase 4):
- `age` ← A's `age` and B's ` Age ` both normalise to `age`
- `city` ← A's `city` and B's `CITY` both normalise to `city`
- `location` and `timestamp` only in B → not shared
- `course` only in A → not shared

