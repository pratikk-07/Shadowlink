# LEARNING GUIDE — SHADOWLINK (Hinglish Edition)

> Yeh guide SHADOWLINK project samajhne ke liye hai — B.Tech final year ke
> students ke liye, jo viva ki preparation kar rahe hain.  Har module ke liye:
> kya hai, kyun hai, kaise kaam karta hai, example, key functions, 5 viva
> questions, aur common mistakes.

---

## Module 1 — Data Profiler (`src/shadowlink/profiler/`)

### Kya hai?

Data Profiler ek CSV file ya DataFrame leke uski "summary report" banata hai.
Jaise doctor patient ka checkup karta hai, profiler data ka checkup karta hai.

### Kyun hai?

Pehle yeh samajhna zaroori hai ki data mein kya hai — kaun se columns hain,
kitni values missing hain, kitni unique values hain — tabhi hum QI identify
kar sakte hain.

### Kaise kaam karta hai?

1. DataFrame ko scan karta hai column by column.
2. Har column ke liye: data type, missing count, distinct count, uniqueness ratio.
3. Duplicate rows count karta hai `DataFrame.duplicated(keep="first")` se.

### Tiny Example

```
age,city,course
20,Kolkata,CSE
20,Kolkata,ECE
21,Delhi,CSE
```

- `age`: 2 distinct (20,21), uniqueness = 2/3 = 0.67
- `city`: 2 distinct, uniqueness = 2/3 = 0.67
- `course`: 2 distinct, uniqueness = 2/3 = 0.67
- `duplicate_row_count = 0`

### Key Functions

| Function | File | Kya karta hai |
|----------|------|---------------|
| `profile_dataframe(df, name)` | `profiler.py` | DataFrame se DatasetProfile banata hai |
| `profile_csv(path, name)` | `profiler.py` | CSV file se DatasetProfile banata hai |

### 5 Viva Questions

**Q1. What is `uniqueness_ratio` and how is it calculated?**
> `uniqueness_ratio = distinct_non_missing / row_count`. Yeh batata hai ki ek
> column kitni "unique" hai.  Age mein 4 distinct values aur 8 rows hain, toh
> ratio = 4/8 = 0.5.

**Q2. Why do we use `keep="first"` in `duplicated()`?**
> `keep="first"` se pehli occurrence ko duplicate nahi mana jata, sirf baad
> wali identical rows ko count kiya jata hai.  Fixture A mein row 5 aur row 6
> dono `22,Delhi,CSE` hain — row 6 ko duplicate count kiya gaya, toh count=1.

**Q3. What is `distinct_count` for a column with missing values?**
> Missing values ko count nahi kiya jata distinct mein.  Sirf non-missing
> unique values count hoti hain.

**Q4. What happens if the input DataFrame has zero rows?**
> `missing_rate` aur `uniqueness_ratio` `None` return karte hain (divide by
> zero avoid karne ke liye).  Yeh "undefined" state hai, zero nahi.

**Q5. Why does `profile_csv` raise `DatasetLoadError` instead of letting pandas raise?**
> Actionable error messages ke liye — pandas ka error message confusing hota hai.
> `DatasetLoadError` mein file path aur exact cause dono mention hote hain.

### Common Mistakes

- ❌ `distinct_count` mein missing values count karna
- ❌ Zero-row DataFrame pe division karna (always check row_count > 0)
- ❌ Caller ka DataFrame mutate karna — SHADOWLINK ke saare functions pure hain

---

## Module 2 — QI Analyser: Equivalence Classes (`src/shadowlink/qi_analyser/`)

### Kya hai?

Quasi-identifier columns ke combination pe records ko groups mein baant ta hai
jahan ek group ke saare records us combination par identical hain.

### Kyun hai?

k-anonymity measure karne ke liye — ek group (equivalence class) mein kitne
records hain, itni zyada "anonymity" hai us record ki.

### Kaise kaam karta hai?

```python
df.groupby(qi_columns)
```

Har unique combination of QI values ek "equivalence class" banata hai.

### Tiny Example (Fixture A, QI=[age,city])

| Group         | Records  | Size |
|---------------|----------|------|
| (20,Kolkata)  | rows 0,1 | 2    |
| (21,Kolkata)  | row 2    | 1    |
| (21,Delhi)    | rows 3,4 | 2    |
| (22,Delhi)    | rows 5,6 | 2    |
| (23,Mumbai)   | row 7    | 1    |

k = min(2,1,2,2,1) = **1**

### 5 Viva Questions

**Q1. What is k-anonymity?**
> k-anonymity guarantee karta hai ki koi bhi record kam se kam k-1 doosre
> records se quasi-identifier pe identical hai.  k=1 matlab koi guarantee nahi.

**Q2. What is a singleton record?**
> Jis equivalence class mein sirf 1 record ho, usse singleton kehte hain.
> Singleton record 100% re-identifiable hai (prosecutor model ke under).

**Q3. What is Discernibility Metric (DM)?**
> DM = Σ|class_size|².  Yeh measure karta hai ki kitna "blurring" hua hai.
> Bada DM = bura utility.

**Q4. Difference between singleton_class_count and singleton_record_count?**
> Ek case: sizes [1, 1, 3].  Singleton classes = 2, singleton records = 2.
> Dusra case: sizes [1, 1, 1] — both are 3.  When all classes are singletons,
> they are equal.  `singleton_record_proportion` uses record count in denominator.

**Q5. What is `missing_policy="own_group"` vs `"exclude_records"`?**
> `own_group`: missing value apna khud ka group banata hai.
> `exclude_records`: missing QI wale records ko analysis se remove karo.

### Common Mistakes

- ❌ k=0 keh dena — agar records_analysed=0 toh k=None
- ❌ Class count vs record count confuse karna in proportions

---

## Module 3 — Risk Engine (`src/shadowlink/risk/`)

### Kya hai?

Equivalence class result se risk metrics calculate karta hai — prosecutor model
ke assumptions ke saath.

### Key Metrics (koi composite score NAHI)

| Metric | Formula |
|--------|---------|
| k | min class size |
| max_class_risk | 1/k |
| average_class_risk | num_classes / records_analysed |
| uniqueness | singleton_records / records_analysed |
| per_record_risk | 1/f for each record |

### 5 Viva Questions

**Q1. What is the prosecutor model?**
> Attacker jaanta hai ki target dataset mein hai, aur QI pe match dhundh raha hai.
> Re-identification probability = 1/f (class size).

**Q2. Why no composite risk score?**
> R3 rule: har metric ka alag formula, denominator, aur assumption hota hai.
> Combine karna misleading hoga — ek number mein sab kuch nahi samaya jata.

**Q3. How is average_class_risk derived?**
> average_class_risk = mean of (1/f) over all records = num_classes/n.
> Proof: Σᵢ fᵢ × (1/fᵢ) / n = num_classes / n.

**Q4. When is max_class_risk = 1.0?**
> Jab k=1, i.e., koi bhi singleton class exist kare toh max_class_risk = 1.0.

**Q5. What if records_analysed = 0?**
> Sab metrics None return karte hain.  Division by zero avoid karna zaroori hai.

---

## Module 4 — Mitigation Engine (`src/shadowlink/mitigation/`)

### Kya hai?

Privacy-preserving transformations apply karta hai aur before/after comparison
deta hai.

### Key Functions

| Function | Kya karta hai |
|----------|---------------|
| `generalize_age` | Age ko bins mein convert karta hai, e.g. 23 → "20-24" |
| `suppress_small_classes` | Small equivalence classes ke records remove karta hai |
| `suppress_rare_values` | Rare values ko "SUPPRESSED" se replace karta hai |
| `coarsen_timestamp` | Timestamp ko hour/day level pe round karta hai |
| `coarsen_coordinates` | Lat/lon precision reduce karta hai |

### Golden Chain on Fixture A

```
Original: N=8, k=1, DM=14
  ↓ generalize_age(width=5)
Generalized: N=8, k=1, DM=26, uniqueness=1/8
  ↓ suppress_small_classes(k=2)
Suppressed: N=7, k=3, DM=25, uniqueness=0
```

### 5 Viva Questions

**Q1. Why does DM increase after generalization even though k stays at 1?**
> Generalization ne classes ko merge kiya — Kolkata(3) aur Delhi(4) bade ho gaye.
> DM = 9+16+1 = 26 > 14.  Mumbai singleton still exists, so k=1 bhi raha.

**Q2. What is the difference between suppress_rare_values and suppress_small_classes?**
> `suppress_rare_values`: ek column ki rare VALUES ko replace karta hai (cell-level).
> `suppress_small_classes`: puri ROWS remove karta hai jahan class < k.

**Q3. Why must mitigation functions be pure (not mutate input)?**
> Caller ka data safe rakhna hai.  Naya DataFrame return karo, original unchanged.

**Q4. What is TransformationResult?**
> `(transformed_df, log)` — transformed DataFrame plus ek log entry jo batata hai
> kya change hua (kind, columns, rows_affected, cells_changed).

**Q5. Can DM decrease while uniqueness also decreases?**
> Haan — suppress_small_classes case mein DM 26→25 aur uniqueness 1/8→0 dono
> decrease hue.  Yeh expected hai.  Platform sirf values report karta hai,
> interpret nahi karta.

---

## Common Viva Topics (All Modules)

**Q. What is the difference between k-anonymity and l-diversity?**
> SHADOWLINK sirf k-anonymity implement karta hai.  l-diversity sensitive attribute
> distribution bhi dekhti hai — scope out of this project.

**Q. Why only synthetic data?**
> R1 rule: Real personal data use karna defensive tool ke liye bhi risky hai.
> Synthetic data se sab algorithms test ho sakte hain bina privacy risk ke.

**Q. What is the safety boundary?**
> Koi bhi column jo ground-truth identity contain kare (ground_truth, true_id,
> true_identity, identity_key) — validation error raise hoti hai.

