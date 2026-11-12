# Decision: Latent Population Sampling Model for Synthetic Data Generation

**Status**: Accepted  
**Phase**: 1 (Generator)

## Context

Benchmarking record linkage and re-identification attacks across multiple heterogeneous datasets requires a realistic population ground truth where the same underlying individual may appear in multiple datasets with consistent attributes prior to noise injection.

## Decision

1. **Single Latent Generation**: Generate a single latent population of $N$ synthetic people once, drawing demographic and behavioral attributes from realistic campus/regional distributions.
2. **Deterministic Partitioning**:
   - $N_{\text{shared}} = \text{round}(f \cdot N)$ people are selected to appear in all released datasets.
   - The remaining $(N - N_{\text{shared}})$ individuals are partitioned among datasets according to `exclusive_weights` using the largest remainder method.
   - Every individual appears in at least one dataset.
3. **Projection then Noise**: Each dataset is a projected view of the latent population over its designated attribute schema. Noise (typos, missing values) is injected strictly *after* projection to model independent observational channel noise.

## Consequences

- Ground truth entity correspondence ($E_i \leftrightarrow \text{record\_id}$) is exact and mathematically consistent.
- Benchmarks reproduce realistic multi-source overlap patterns with verifiable parameters.

