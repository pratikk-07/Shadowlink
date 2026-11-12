# SHADOWLINK Part 2 — Viva Preparation & Learning Guide (Hinglish)

Yeh guide SHADOWLINK ke Part 2 modules (Synthetic Data Generator, Linkage Engine, Attacker Simulator, Evaluator) ke core concepts, algorithms, real code examples aur viva examination questions ko cover karti hai.

---

## 1. Synthetic Data Generator (`shadowlink.generator`)

### 1.1 Kya karta hai? (What it is)
Yeh module realistic synthetic tabular datasets generate karta hai jisme:
- Ek common **latent population** ($N$ log) banti hai.
- Fixed fraction ($f$) log multiple datasets (A, B, C) me **shared** hote hain.
- Non-shared log **exclusive** hote hain.
- Realistic **observational noise** (typos via single edit operations aur missing values) inject kiya jata hai.
- Strict **Ground Truth isolation**: entity IDs sirf alag `ground_truth.csv` file me likhe jaate hain, datasets me kabhi save nahi hote.

### 1.2 Kyun zaroori hai? (Why it is needed)
Real personal data use karna privacy violation aur illegal ho sakta hai (DPDP Act / GDPR). Record linkage aur attacker algorithms ko rigorously test aur benchmark karne ke liye hume aisa data chahiye jiska ground truth mathematically verified ho aur configurable noise rates ho.

### 1.3 Kaise kaam karta hai? (How it works internally)
1. **Latent Population**: `generate_latent_population(N, seed)` se $N$ logo ki latent profile banti hai (age, city, course, hostel, club, location, timestamp).
2. **Partitioning**: $N_{\text{shared}} = \text{round}(f \cdot N)$ log sabhi datasets me aate hain. Remaining exclusive logo ko `exclusive_weights` ke largest remainder method se baanta jata hai.
3. **Projection**: Har dataset schema ke hisaab se latent attributes project hote hain.
4. **Noise Injection**:
   - `typo_rate`: String cells me exactly ek random edit (substitute, delete, insert, ya adjacent transposition). Guaranteed ki mutated string original se alag ho aur empty na ho.
   - `missing_rate`: Cells ko random missing (`None`/`NaN`) set kiya jata hai.
5. **Row Shuffling & Record ID**: Rows ko random shuffle karke opaque IDs (e.g. `A-00001`, `B-00017`) assign hote hain taaki row order se koi identity leak na ho.

### 1.4 Code Example
```python
from shadowlink.generator.generator import report_abc
from shadowlink.generator.io import write_bundle

# Generate preset A, B, C bundle
bundle = report_abc(seed=42, population_size=500, shared_fraction=0.5)
write_bundle(bundle, "./data/generated")
```

### 1.5 Top 5 Viva Questions & Answers
**Q1: Datasets me `entity_id` kyun nahi rakha gaya?**  
*Ans*: Rule R2 (Ground Truth Boundary) ke tehat datasets completely unlinked hone chahiye. Agar dataset me `entity_id` hota toh linkage ya attacker algorithm use "cheat" kar sakte the. Isliye ground truth alag file me rehta hai.

**Q2: Largest remainder method ka use partitioning me kyun kiya gaya?**  
*Ans*: Float counts (jaise $0.33 \times 100 = 33.33$) ko integer me convert karte waqt simple rounding se sum $N$ se kam ya zyada ho sakta hai. Largest remainder method exact total preserve karta hai deterministically.

**Q3: Typo injection me kaunse edits allow hain?**  
*Ans*: Damerau-Levenshtein 4 elementary edits: Single character substitution, single character deletion, single character insertion, aur adjacent character transposition.

**Q4: Row shuffling record_id assign karne se pehle kyun hoti hai?**  
*Ans*: Agar shuffling na ho, toh record `A-00001` aur `B-00001` dono same latent person represent karenge, jisse attacker direct ID matching se break kar lega. Shuffling guarantees zero identity leakage in row index.

**Q5: `manifest.json` me kya store hota hai?**  
*Ans*: Configuration parameters, seed, Python/Pandas/Numpy versions, dataset row counts, shared overlap counts, aur injected typos/missing cell counts reproducibility audit ke liye.

---

## 2. Record Linkage Engine (`shadowlink.linkage`)

### 2.1 Kya karta hai? (What it is)
Yeh module bina ground-truth dekhe alag-alag datasets ke records ko match karta hai:
- **String Comparators**: Pure Python from-scratch Levenshtein, Jaro, Jaro-Winkler.
- **Blocking**: Multi-pass blocking jo comparison space ko $90\%+$ reduce karta hai.
- **Methods**: Deterministic (Exact), Weighted Similarity, aur Fellegi-Sunter Weight of Evidence.
- **Clustering**: Union-Find data structure se transitive closure clusters banana aur intra-dataset collisions detect karna.

### 2.2 Kyun zaroori hai? (Why it is needed)
Data release ke baad attacker ya researcher do alag sources (e.g. hospital records + voter list) ko link karke identities expose kar sakte hain. Is engine se hum quantify karte hain ki noisy attributes me linkage kitni accurately ho sakti hai.

### 2.3 Key Algorithms & Formulas
1. **Levenshtein**: Edit distance normalized by $\max(|s_1|, |s_2|)$.
2. **Jaro**: Window $W = \lfloor \max(|s_1|, |s_2|)/2 \rfloor - 1$. Matched characters $m$ aur transpositions $t$ calculate hote hain: $\text{sim}_J = \frac{1}{3} (\frac{m}{|s_1|} + \frac{m}{|s_2|} + \frac{m-t}{m})$.
3. **Jaro-Winkler**: Prefix bonus: $\text{sim}_{JW} = \text{sim}_J + \ell \cdot p \cdot (1 - \text{sim}_J)$ where $\ell = \min(4, \text{prefix})$.
4. **Fellegi-Sunter**:
   - $w_i^{\text{agree}} = \log_2(m_i / u_i)$
   - $w_i^{\text{disagree}} = \log_2((1 - m_i) / (1 - u_i))$
   - Total weight score $\ge T_{\text{upper}} \implies \text{match}$.

### 2.4 Code Example
```python
from shadowlink.linkage.blocking import BlockingPass, generate_candidate_pairs
from shadowlink.linkage.methods import similarity_linkage
from shadowlink.linkage.models import AttributeComparatorSpec

# Block on city
b_pass = BlockingPass(columns=["city"])
cands, report = generate_candidate_pairs(df_a, df_b, [b_pass])

# Approximate similarity matching
specs = [AttributeComparatorSpec(attribute="age", method="exact")]
preds = similarity_linkage(df_a, df_b, cands, specs, threshold=0.85)
```

### 2.5 Top 5 Viva Questions & Answers
**Q1: Jaro aur Levenshtein me kya practical difference hai?**  
*Ans*: Levenshtein generic edit distance hai jisme substitutions aur insertions ka cost constant hota hai. Jaro specially short strings aur names ke liye design kiya gaya hai jisme character matching window aur transpositions factor hote hain, jisse spelling typos par better score milta hai.

**Q2: Blocking kyun zaroori hai? Iske do key evaluation metrics kya hain?**  
*Ans*: Agar blocking na karein toh dono tables ka Cartesian product $N_A \times N_B$ compare karna padega ($O(N^2)$), jo computational bottleneck hai. Key metrics: **Reduction Ratio (RR)** (kitne comparisons bache) aur **Pairs Completeness (PC)** (kitne true matches candidate set me retain huye).

**Q3: Fellegi-Sunter theory me $m$ aur $u$ probabilities kya represent karti hain?**  
*Ans*: $m_i = P(\text{agree}_i \mid \text{True Match})$ (match hone par agreement ki probability, e.g. $0.95$). $u_i = P(\text{agree}_i \mid \text{Non-Match})$ (coincidental agreement chance among different people, e.g. $0.05$).

**Q4: Disagreement weight negative kyun hoti hai?**  
*Ans*: Formula $w^{\text{disagree}} = \log_2((1-m)/(1-u))$. Kyunki true matches me disagreement rare hota hai ($1-m < 1-u$), ratio $< 1$ hoti hai, jiska $\log_2$ strictly negative weight evidence deta hai.

**Q5: Union-Find clustering me collision detection ka kya role hai?**  
*Ans*: Ek hi dataset ke do alag records (e.g. `A-00001` aur `A-00002`) agar same cluster me merge ho jaayein, toh use intra-dataset collision kehte hain (kyunki ek dataset me person unique hona chahiye). Union-Find is collision ko flag karta hai 1-to-1 matching violations pakadne ke liye.

---

## 3. Attacker Simulator (`shadowlink.attacker`)

### 3.1 Kya karta hai? (What it is)
Yeh module ek **prosecutor threat model** simulate karta hai:
- Ek attacker ke paas target individual ke bare me auxiliary information hai.
- Attacker step-by-step additional quasi-identifiers reveal karta hai: (1) Age + City $\implies$ (2) +Course $\implies$ (3) +Location $\implies$ (4) +Timestamp.
- Har step par candidate set $C_j$ narrow hota hai.
- Candidate risk $R = 1/|C_j|$ compute hota hai.

### 3.2 Kyun zaroori hai? (Why it is needed)
Data release karne se pehle publish karne wale ko pata hona chahiye ki agar adversary ke paas specific auxiliary attributes hain, toh target person kitni aasani se uniquely re-identify ho jayega.

### 3.3 Key Invariants & Formulas
1. **Monotonicity**: Har step par candidate set ya toh narrow hoga ya same rahega ($C_{j} \subseteq C_{j-1}$), candidate count kabhi badh nahi sakta.
2. **Prosecutor Assumption**: Target individual hamesha target dataset ke andar maujood hota hai.
3. **Consistency with Class Risk**: Equal auxiliary knowledge par mean candidate risk exact population equivalence class risk ke barabar hota hai.

### 3.4 Code Example
```python
from shadowlink.attacker.models import AttackerProfile
from shadowlink.attacker.simulator import simulate_attack

profile = AttackerProfile.strong()  # 4-step disclosure
result = simulate_attack(df, profile=profile, n_targets=100, seed=42)
print(result.to_dataframe())
```

### 3.5 Top 5 Viva Questions & Answers
**Q1: Prosecutor model aur Journalist model me kya difference hai?**  
*Ans*: Prosecutor model me attacker target person ko specific maanta hai aur janta hai ki target dataset me maujood hai ($R = 1/c$). Journalist model me attacker kisi bhi arbitrary person ko re-identify karne ki koshish karta hai without knowing if target is present.

**Q2: Progressive attribute disclosure monotonicity kyun satisfy karni chahiye?**  
*Ans*: Information theory ke according, additional attributes add karne se filtering criteria sirf strict hota hai, kabhi relax nahi hota. Isliye candidates set size non-increasing hona chahiye: $|C_{j}| \le |C_{j-1}|$.

**Q3: Table 5 experiment se kya conclusion nikalta hai?**  
*Ans*: Sirf demographic baseline (Age, City) se identification risk low (21.3%) aur uniqueness sirf 1% rehti hai. Lekin temporal (timestamp) ya spatial (location) data add hote hi uniqueness 91% se 100% tak shoot kar jaati hai.

**Q4: Agar target person ka koi attribute missing ho toh simulation kaise handle karti hai?**  
*Ans*: Attacker us particular attribute ko skip karta hai aur candidate set narrow nahi hota, preserving defensive neutrality.

**Q5: Candidate risk $R = 1/c$ ka real-world meaning kya hai?**  
*Ans*: Agar equivalence class me 5 log match hote hain ($c=5$), toh attacker ka random guess sahi hone ki probability $1/5 = 0.20$ (20%) hai. Jab $c=1$, confidence 100% (deterministic re-identification) hoti hai.

---

## 4. Evaluator & Mitigation Evaluation (`shadowlink.evaluator`)

### 4.1 Kya karta hai? (What it is)
Yeh module platform ka verification authority hai:
- Linkage predictions ko ground truth se compare karke **Precision, Recall, F1-Score** nikalta hai.
- Multi-pass blocking ki **Pairs Completeness** aur **Reduction Ratio** evaluate karta hai.
- Ground truth training data se **Laplace smoothed $m$ aur $u$ probabilities** calibrate karta hai.
- **Privacy-Utility Tradeoffs** evaluate karta hai (Table 7) under worst-case attacker assumptions.

### 4.2 Key Formulas
1. **Precision**: $\frac{\text{TP}}{\text{TP} + \text{FP}}$ (Predicted matches me kitne actual true matches hain).
2. **Recall**: $\frac{\text{TP}}{\text{TP} + \text{FN}}$ (Total true matches me se kitne model ne dhoondhe).
3. **F1-Score**: Harmonic mean: $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$.
4. **Laplace Smoothing in Calibration**:
   $$m_i = \frac{N_{\text{agree}, M} + 1}{N_M + 2}, \quad u_i = \frac{N_{\text{agree}, U} + 1}{N_U + 2}$$
   Guarantees $0 < m_i, u_i < 1$ even with zero observations.

### 4.3 Code Example
```python
from shadowlink.evaluator.experiments import run_table6_experiment, run_table7_experiment

# Run Table 6 Linkage Benchmark
df6, md6, csv6 = run_table6_experiment(n=500, seed=42)

# Run Table 7 Mitigation Tradeoffs
df7, md7, csv7 = run_table7_experiment(n=500, seed=42)
```

### 4.4 Top 5 Viva Questions & Answers
**Q1: Laplace smoothing calibration me kyun compulsory hai?**  
*Ans*: Agar sample me kisi attribute par zero disagreements hon ($N_{\text{agree}} = N$), toh unsmoothed probability $1.0$ ban jayegi. Fellegi-Sunter weight me $\log_2(0)$ ya division by zero hone se math error crash ho jayega. Laplace smoothing guarantees valid finite probabilities.

**Q2: Tie-adjusted success rate deterministic tie-breaking se better metric kyun hai?**  
*Ans*: Deterministic tie-breaking (e.g. minimum ID pick karna) arbitrary ordering par depend karta hai jo true ability reflect nahi karta. Tie-adjusted metric exact mathematical expected value ($1/c$) provide karta hai.

**Q3: K-Anonymity mitigation se Linkage F1 score par kya asar padta hai?**  
*Ans*: Table 7 results dikhate hain ki 5-year age generalization se max class risk $1.0 \implies 0.5$ aur uniqueness $5.09\% \implies 0.00\%$ drop ho jaati hai, jisse privacy secure hoti hai. Iska tradeoff yeh hai ki Linkage F1 score $0.3367 \implies 0.1067$ degrade ho jata hai kyunki matches ambiguous ho jaate hain.

**Q4: Worst-case Kerckhoffs assumption kya hai mitigation evaluation me?**  
*Ans*: Hum assume karte hain ki attacker ko exactly pata hai ki dataset par konsi transformation (e.g. 5-year age binning) lagayi gayi hai, aur attacker apne auxiliary data ko bhi usi form me harmonize karke attack karta hai.

**Q5: Pairs Completeness aur Recall me kya difference hai?**  
*Ans*: Pairs Completeness blocking stage ka recall hai (kya true matches candidate pairs ke pool me aaye?). Recall final linkage decision ka metric hai (kya true matches ko engine ne 'match' classify kiya?). PC is the theoretical upper bound for linkage recall.

