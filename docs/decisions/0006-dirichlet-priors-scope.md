# ADR-0006 : Dirichlet priors on transitions (MAP smoothing)

**Date** : 2026-05-22
**Status** : Accepted

## Context

Sub-project A's fit produces a maximum-likelihood transition matrix.
Pragmatic ML workflows often want:
- **Smoothing** to avoid exact-zero or exact-one transitions on small data.
- **Soft structural priors** to express "this transition is probably rare
  but possible" (e.g., (vol → calm) is allowed but unusual).
- **Bayesian inference** with explicit priors and posterior credible
  intervals.

A.9 covers cases (1) and (2) via MAP smoothing. Case (3) — full Bayesian
posterior — is out of scope (would need hmm-bayes or pomegranate).

## Decision

Add two optional fields to `Topology`:

- **`transmat_prior_alpha: float | None`** — scalar symmetric Dirichlet(α)
  prior on every allowed edge. α=1 → uniform → MLE (current). α>1 →
  smoothing toward uniform. α<1 → sparsification (rare; theoretical).
- **`transmat_prior_matrix: list[list[float]] | None`** — explicit (K, K)
  per-edge pseudo-counts. Overrides `transmat_prior_alpha` when set.
  Forbidden edges are re-masked to 0.

In `Constrained*HMM._do_mstep`, after the standard M-step:

    transmat_post = MAP(transmat, prior, mask)

via the new helper `_map_update` in `fit/_base.py`. The MAP update treats
the prior as pseudo-counts blended with the EM-derived counts:

    posterior_count[i, j] = transmat[i, j] * effective_n + (prior[i, j] - 1)
    posterior_count *= mask
    transmat_post[i] = posterior_count[i] / sum(posterior_count[i])

Default `effective_n = 1.0` — the prior counts as one effective
observation per row. Users tune by scaling the prior themselves.

## Alternatives considered

- **Full variational Bayes / Gibbs sampling.** Right answer for credible
  intervals on the transition matrix. But ~10x the code, and outside the
  hmmlearn paradigm. Deferred to a future `hmm-bayes` project.
- **Per-iteration prior decay** (so the prior dominates early in EM,
  fades to the data later). Common heuristic. Deferred to A.9.1.
- **Priors on emissions** (means, covariances). Different math; same
  scope arguments. Deferred to A.9.2.

## Consequences

### Positive
- Backward compat: both new fields default to `None`. Existing tests pass.
- Users can express soft structural priors without changing the EM core.
- Sparse / left-right topologies benefit from regularization on small data.

### Negative
- The MAP update is a heuristic — not the formal posterior. Documented in
  the ADR and in the function docstring.
- `effective_n=1.0` is opinionated. Tuning it is left to the user (scale
  the prior values).
- Convergence behavior with strong priors is not extensively characterized;
  callers should sanity-check `log_likelihood` and `converged`.

## Tests that validate this decision

- `tests/test_priors.py` — 12 tests covering: validation, prior() matrix
  building, MAP update math, mask compatibility, fit() smoke, YAML
  roundtrip.

## Revisit triggers

- Demand for credible intervals on A → open A.9.x or new project
  `hmm-bayes`.
- Strong priors cause numerical instability in real fits → adjust
  `effective_n` (per-iteration scaling).
- Demand for emission priors → open A.9.2 (priors on means/covars/lambda).

## Pointers

- `src/hmm_core/topology.py` (transmat_prior_alpha, transmat_prior_matrix, transmat_prior())
- `src/hmm_core/fit/_base.py:_map_update`
- `src/hmm_core/fit/{gaussian,gmm,multinomial,poisson}.py` (use _map_update in _do_mstep)
- `tests/test_priors.py`
- ADR-0001 (backend choice) — explains why we patch hmmlearn rather than switch
- ADR-0003 (backend abstraction) — Protocol extended with `transmat_prior`
