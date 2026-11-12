# Decision: Forbidden Column Names

**Status**: Accepted  
**Phase**: 0 (Foundation)

## Context

SHADOWLINK must never receive or process ground-truth identity information.
Even if a caller accidentally passes a DataFrame that still contains an identity
key, the system must reject it rather than silently processing it.

## Decision

The following column names are **unconditionally rejected** at every public API
boundary (case-insensitive, strip-then-lowercase check):

| Forbidden name   | Why it is forbidden |
|------------------|---------------------|
| `ground_truth`   | Direct identity label produced by Synthetic Data Generator |
| `true_id`        | Alternative identity key naming convention |
| `true_identity`  | Long-form alternative |
| `identity_key`   | Generic identity-key naming convention |

A `ValidationError` is raised immediately with an actionable message.

## Consequences

- Callers must remove identity columns before passing data to any SHADOWLINK function.
- The error message tells the caller what to remove and why.
- A companion signature-inspection test (`TestPublicFunctionSignatures`) ensures
  that no parameter of any public function carries these names.

