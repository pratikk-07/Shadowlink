# Decision: Ground Truth Boundary Isolation

**Status**: Accepted  
**Phase**: 5 (Evaluator)

## Context

In re-identification risk evaluation and record linkage benchmarking, algorithms must never peek at ground-truth entity labels during feature comparison, blocking, candidate scoring, or attacker simulation. Allowing ground-truth identity information into linkage or attacker modules introduces leakage and compromises the validity of privacy guarantees.

## Decision

1. **Strict Module Boundary**: Only `shadowlink.evaluator` and the generator writer `shadowlink.generator.io` are permitted to load or access ground truth.
2. **Forbidden Imports & Identifiers**: Modules under `shadowlink.linkage` and `shadowlink.attacker` must never import `shadowlink.evaluator`, nor reference `ground_truth`, `entity_id`, `true_id`, or `identity_key`.
3. **Automated Enforcement**: Enforced by AST static analysis and signature inspection in test suite (`tests/unit/test_evaluator.py`).

## Consequences

- Linkage methods and attacker simulators output purely statistical candidates and scores indexed by `record_id`.
- Ground truth evaluation happens purely as a post-hoc verification step within `evaluator`.

