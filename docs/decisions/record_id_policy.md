# Decision: Record ID Generation and Exclusion Policy

**Status**: Accepted  
**Phase**: 1 (Generator)

## Context

Datasets require unique row keys for referencing candidate pairs and linkage decisions. However, sequential row ordering or sequential IDs can leak latent person identities if not carefully isolated.

## Decision

1. **Post-Shuffle Assignment**: Record IDs (e.g. `A-00001`, `B-00042`) are assigned strictly *after* rows have been randomly shuffled using the seeded RNG.
2. **Opaque and Dataset-Scoped**: Each ID encodes only the dataset prefix and an opaque zero-padded index. It carries zero information about row generation order or latent entity ID.
3. **QI Exclusion**: `record_id` is an internal row pointer and must always be excluded from quasi-identifier analysis, risk profiling, and equivalence class computation.

## Consequences

- No re-identification attack can exploit row position or record ID ordering.
- Linkage candidate pairs are cleanly identified by `(left_id, right_id)`.

