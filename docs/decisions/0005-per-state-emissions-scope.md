# ADR-0005 : Per-state EmissionSpec — scope and constraints

**Date** : 2026-05-22
**Status** : Accepted

## Context

Sub-project A's `Topology` carried a single `emission: EmissionSpec` for all
K states. Several real workflows want **per-state init hints** (e.g., user
knows state "crash" should start near mean=-3.0, state "calm" near 0.0).

## Decision

Add an OPTIONAL `Topology.emissions: list[EmissionSpec] | None` field. When
provided:
- Must have `len(emissions) == n_states`.
- All entries must share `type` and hyperparams (`n_features`,
  `covariance_type`, `n_mix`, `n_symbols`) with `Topology.emission`.
- New optional init-hint fields on `EmissionSpec`:
  `init_mean`, `init_covar`, `init_lambda`, `init_emissionprob`.
- `init.emission_params()` overrides the kmeans/uniform defaults with the
  per-state hints when present.

## Alternatives considered

- **Heterogeneous types per state** (state 0 gaussian, state 1 multinomial).
  Requires custom EM (hmmlearn assumes single-type). Deferred to A.8.x.
- **Different `covariance_type` per state**. Same constraint. Deferred.
- **Different `n_mix` per state for GMM**. Same constraint. Deferred.

## Consequences

### Positive
- Existing topologies (`emission: ...` only) continue to work unchanged.
- Users can guide EM with prior knowledge (often makes convergence faster
  and to better local optima).
- Lays the groundwork for B.4.2 — per-state emission UI in the React Flow
  editor.

### Negative
- The constraint "all entries must share hyperparams" is real and will
  surprise users who expect full per-state flexibility. Mitigation: clear
  error messages reference "planned A.8.x".

### Out of scope (future)
- A.8.1 — per-state `covariance_type` (requires custom EM or pomegranate backend).
- A.8.2 — mixed emission types per state (same).
- A.9 — Dirichlet priors on transitions (orthogonal).
