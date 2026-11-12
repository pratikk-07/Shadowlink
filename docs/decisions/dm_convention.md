# Decision: Discernibility Metric (DM) Convention

**Status**: Accepted  
**Phase**: 2 and 5

## Definition

```
DM = Σᵢ |Cᵢ|²
```

where the sum is over all equivalence classes *Cᵢ*.

## Interpretation

- **Higher DM = worse utility**: records in large classes are indistinguishable
  from more people, so answers to aggregate queries are less precise.
- A perfectly specific dataset (all classes size 1) has `DM = n`.
- A fully suppressed dataset (one class of size n) has `DM = n²`.

## Comparison guidance

Always state **record counts alongside DM** when comparing two frames:
a mitigation may suppress records (reducing n) while also raising DM if the
remaining records cluster into larger classes.

## Worked Example

Fixture A, QI=[age,city]: sizes {2,1,2,2,1}
`DM = 4+1+4+4+1 = 14`

After generalize_age: sizes {3,4,1}
`DM = 9+16+1 = 26`  ← DM increased even though uniqueness decreased.
This is expected and documented behaviour; the platform reports both values
without interpreting direction.

After suppress_small_classes(k=2): sizes {3,4}, N=7
`DM = 9+16 = 25`  ← DM decreased because one record was removed.

