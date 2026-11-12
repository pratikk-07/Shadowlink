# Mathematical Foundations of Record Linkage & Attacker Simulation

This document provides formal definitions, mathematical formulas, and hand-worked step-by-step examples for every algorithm implemented in the second half of the SHADOWLINK platform.

---

## 1. String Comparators

### 1.1 Levenshtein Distance & Normalized Similarity
Given two strings $s_1$ and $s_2$ of lengths $|s_1|$ and $|s_2|$, the Levenshtein distance $D_L(s_1, s_2)$ is the minimum number of single-character edits (insertions, deletions, or substitutions) required to transform $s_1$ into $s_2$.

$$\text{sim}_L(s_1, s_2) = 1.0 - \frac{D_L(s_1, s_2)}{\max(|s_1|, |s_2|)}$$

#### Hand-worked Example: `KITTEN` vs `SITTING`
1. `KITTEN` -> `SITTEN` (Substitute S for K) -> 1
2. `SITTEN` -> `SITTIN` (Substitute I for E) -> 2
3. `SITTIN` -> `SITTING` (Insert G) -> 3
- $D_L = 3$, $\max(6, 7) = 7$
- $\text{sim}_L = 1 - 3/7 = 4/7 \approx 0.5714$.

---

### 1.2 Jaro Similarity
Given strings $s_1$ and $s_2$, matching window is:
$$W = \max\left(0, \left\lfloor \frac{\max(|s_1|, |s_2|)}{2} \right\rfloor - 1\right)$$

Two characters at $s_1[i]$ and $s_2[j]$ match if $s_1[i] == s_2[j]$ and $|i - j| \le W$.
Let $m$ be the number of matched characters. If $m = 0$, $\text{sim}_J = 0.0$.
Let $t$ be half the number of character transpositions between matching characters:

$$\text{sim}_J(s_1, s_2) = \frac{1}{3} \left( \frac{m}{|s_1|} + \frac{m}{|s_2|} + \frac{m - t}{m} \right)$$

#### Hand-worked Example: `MARTHA` vs `MARHTA`
- $|s_1| = 6, |s_2| = 6$.
- $W = \lfloor 6/2 \rfloor - 1 = 2$.
- Matching characters: $m = 6$ (`M, A, R, T, H, A`).
- Order in $s_1$: `M-A-R-T-H-A`.
- Order in $s_2$: `M-A-R-H-T-A`.
- Characters `T` and `H` are transposed: 2 non-matching positions $\implies t = 2/2 = 1$.
- $\text{sim}_J = \frac{1}{3} \left( \frac{6}{6} + \frac{6}{6} + \frac{6 - 1}{6} \right) = \frac{1}{3} (1 + 1 + 5/6) = \frac{17}{18} \approx 0.9444$.

---

### 1.3 Jaro-Winkler Similarity
Standard Jaro similarity modified by common prefix scaling:
$$\text{sim}_{JW}(s_1, s_2) = \text{sim}_J + \ell \cdot p \cdot (1 - \text{sim}_J)$$
Where:
- $\ell = \min(4, \text{length of common prefix up to 4 characters})$.
- $p$ is the prefix scaling factor (standard $p = 0.1$, constraint $p \cdot \ell \le 1$).

#### Hand-worked Example: `MARTHA` vs `MARHTA`
- Common prefix: `MAR` $\implies \ell = 3$.
- $\text{sim}_{JW} = 0.9444 + 3 \cdot 0.1 \cdot (1 - 0.9444) = 0.9444 + 0.3 \cdot (0.0556) = 0.9444 + 0.0167 = 0.9611$.

---

## 2. Multi-Pass Candidate Pair Blocking

Given datasets $A$ and $B$ with sizes $|A|$ and $|B|$, the naive Cartesian product size is $|A \times B| = |A| \cdot |B|$.
Let $C \subseteq A \times B$ be the generated set of candidate pairs.
Let $M \subseteq A \times B$ be the set of true matching pairs.

### 2.1 Reduction Ratio (RR)
Proportion of unneeded pair comparisons eliminated by blocking:
$$\text{RR} = 1.0 - \frac{|C|}{|A| \cdot |B|}$$

### 2.2 Pairs Completeness (PC / Recall of Blocking)
Proportion of all true matching pairs retained in candidate set $C$:
$$\text{PC} = \frac{|C \cap M|}{|M|}$$

---

## 3. Fellegi-Sunter Weight of Evidence Theory

For each attribute $i \in \{1, \dots, K\}$, define conditional probabilities:
- $m_i = P(\text{agree}_i \mid (a, b) \in M)$ (Match probability)
- $u_i = P(\text{agree}_i \mid (a, b) \in U)$ (Unmatched / non-match probability)

### 3.1 Weight Formulas
- Agreement Weight:
  $$w_i^{\text{agree}} = \log_2 \left( \frac{m_i}{u_i} \right)$$
- Disagreement Weight:
  $$w_i^{\text{disagree}} = \log_2 \left( \frac{1 - m_i}{1 - u_i} \right)$$
- Missing attribute value: $w_i^{\text{missing}} = 0.0$.

### 3.2 Total Pair Score
$$\text{Score}(a, b) = \sum_{i=1}^K w_i$$
Decision Rule:
$$\text{Decision}(a, b) = \begin{cases}
\text{match} & \text{if } \text{Score}(a, b) \ge T_{\text{upper}} \\
\text{non\_match} & \text{if } \text{Score}(a, b) \le T_{\text{lower}} \\
\text{possible} & \text{if } T_{\text{lower}} < \text{Score}(a, b) < T_{\text{upper}}
\end{cases}$$

#### Hand-worked Specification Oracle:
Given $m_1 = 0.90, u_1 = 0.20$:
$$w_1^{\text{agree}} = \log_2(0.90 / 0.20) = \log_2(4.5) \approx 2.169925$$
$$w_1^{\text{disagree}} = \log_2((1 - 0.90) / (1 - 0.20)) = \log_2(0.10 / 0.80) = \log_2(0.125) = -3.000000$$

---

## 4. Re-Identification Success Metrics

Under prosecutor attack scenario, an attacker targets individual $t \in A$ and retrieves candidate set $C_t \subseteq B$ of records sharing matching attributes.
Let $c_t = |C_t|$ be the candidate set size.
Let $r_t^* \in B$ be the true counterpart record for entity $t$.

### 4.1 Candidate Risk
If target counterpart is in $C_t$:
$$R(t) = \frac{1}{c_t}$$

### 4.2 Tie-Adjusted Success Rate
Credit allocated to target $t$:
$$\text{Credit}(t) = \begin{cases}
\frac{1}{c_t} & \text{if } r_t^* \in C_t \\
0.0 & \text{if } r_t^* \notin C_t
\end{cases}$$

$$\text{Success}_{\text{tie-adjusted}} = \frac{1}{|A|} \sum_{t \in A} \text{Credit}(t)$$

### 4.3 Deterministic Tie-Breaking
When an attacker breaks ties by deterministically picking the candidate record with the lexicographically smallest `record_id`:
$$\text{Success}_{\text{deterministic}} = \frac{1}{|A|} \sum_{t \in A} \mathbb{I}(\text{pick}(C_t) == r_t^*)$$

