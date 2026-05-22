# ADR-0007 : GMM-NHMM scope (Phase A.10 MVP)

**Date** : 2026-05-22
**Status** : Accepted

## Context

The crypto-modeling use case (Phase D) needs a model that combines:
- **GMM emissions** per state (to capture sub-modes within a regime, e.g.
  "bull-smooth" vs "bull-explosive" inside a "bull" regime)
- **NHMM transitions** (covariates like funding rate, realized vol, volume
  drive regime transitions)

Neither `hmmlearn` nor `pomegranate` nor `sequentia` ships this combination.
This ADR scopes the MVP implementation.

## Decision

Implement **Stratégie A** (two-stage fit) for the MVP:

1. **Stage 1**: fit a standard `hmmlearn.GMMHMM` on X, ignoring Z. This
   gives the per-state GMM emission parameters and the Viterbi state path
   under a homogeneous transition matrix.
2. **Stage 2**: for each source state i, fit a multinomial logistic
   regression of `next_state[t+1] | Z[t]` on the observed pairs
   `(Z[t], z[t+1])` from the Viterbi path. The resulting per-state
   classifiers give us `A_ij(Z[t])` = covariate-dependent transitions.

The result is a `GMMNHMMFittedModel` with the same shape as `NHMMFittedModel`
(Phase A.1) — wrapping a `base` FittedModel + an `A_t` (T, K, K) tensor +
per-state classifiers.

## Alternatives considered

- **Stratégie B (full joint EM)**: jointly update emissions, mixture
  weights, and covariate-dependent transitions in a single EM loop. More
  correct (the two-stage approach loses information by conditioning Stage
  2 on Stage 1's Viterbi rather than the posterior). 1-2 weeks of work,
  requires writing a custom EM loop outside hmmlearn's framework.
  **Deferred to A.10.x** when the MVP proves its value in Phase D.
- **Switch to pomegranate backend**: pomegranate v1 supports both GMM
  emissions and structured transitions, but covariate-dependent transitions
  would still need a custom layer. Backend swap for a single feature is
  over-engineering. Stay on hmmlearn.

## Consequences

### Positive
- Reuses the proven Phase A.1 pattern (`fit_nhmm`); minimal new surface.
- Works with the existing `HMMBackend` Protocol (no protocol changes).
- Mask-respected `A_t` via `_apply_mask` per row per t.
- Ships in 3-5 days; immediately usable from Phase D dashboard.

### Negative
- **Statistical efficiency lost**: Stage 2 uses Viterbi (point estimate)
  rather than the forward-backward posterior. Soft state assignments
  (γ_t(k)) would weight the logistic regression more correctly.
- **No identifiability constraint** on the logistic regression: with K
  classes per source state, the reference category is sklearn's choice,
  not a documented convention.
- **No per-state mixture count**: `n_mix` is global. Different states
  might genuinely need different mixture sizes (e.g., a "calm" regime
  with M=1 and a "vol" regime with M=3). Deferred.

### Validation
- Phase V suite should cross-check `fit_gmm_nhmm` against a manual joint
  EM implementation on a small synthetic dataset (deferred to V follow-up
  when Stratégie B lands and we have a reference).

## Revisit triggers
- Phase D crypto dashboard adopts GMM-NHMM and finds the two-stage fit
  insufficient (e.g., Stage 1 collapses sub-modes that Stage 2 needs).
- A second use case (academic, bioinfo) demands per-state `n_mix`.
- Joint EM (Stratégie B) becomes a research priority.

## Pointers
- `src/hmm_core/gmm_nhmm.py` (this implementation)
- `src/hmm_core/nhmm.py` (the Phase A.1 NHMM that this mirrors)
- `tests/test_gmm_nhmm.py`
- ADR-0003 (backend abstraction — `HMMBackend` Protocol unchanged here)
- Phase A.10 full spec: `docs/specs/2026-05-22-phase-a10-gmm-nhmm.md`
