# Scientific validation suite — Phase V

> **What this is** : tests verifying that our HMM implementations produce
> the right *numerical* answers, against canonical references where the
> answer is known analytically or by published reference.
>
> **What this is NOT** : code-correctness tests. Those live in `tests/`.
>
> Separate suites because validation tests can be slow, sometimes flaky on
> statistical thresholds, and they reference external work that
> stakeholders (reviewers, profs) might check.

## Running

```bash
# Full suite
pytest validation/ -v

# One layer
pytest validation/test_v1_cross_check_hmmlearn.py -v

# Skip slow tests
pytest validation/ -v -m "not slow"
```

The validation suite is **not** run by default `pytest` (which uses
`testpaths = ['tests']`). Run it explicitly when releasing, bumping
`hmmlearn`, or adding a new backend.

## Status per layer

| Layer | Description | Status | Tests | Sources |
|---|---|---|---|---|
| **V.1** | Cross-check vs `hmmlearn` baseline (sanity) | ✅ **SHIPPED** (2026-05-22) | 4/4 passing | hmmlearn 0.3.x as reference |
| **V.2** | Recovery on synthetic data (statistical correctness) | ✅ **SHIPPED** (2026-05-22) | 5/5 passing | Law of large numbers + Hungarian matching |
| **V.3** | Textbook canonical problems (analytical correctness) | ✅ **SHIPPED** (2026-05-22) | 6/6 passing | Russell & Norvig (AIMA), Durbin et al., Eisner |
| **V.4** | Numerical stability stress | ✅ **SHIPPED** (2026-05-22) | 5/5 passing | Long sequences, near-singular cov, rare states, K=15 |
| **V.5** | Cross-check A.10 GMM-NHMM strategies | ⏳ TODO (gated on A.10) | 3-4 | Self-consistency Strategy A vs B |
| **V.6** | Cross-check A.13 Factorial NHMM strategies | ⏳ TODO (gated on A.13) | 3-4 | Self-consistency Strategy A vs B |

## Quick stats (2026-05-22 PM)

- **20 tests** total across V.1, V.2, V.3, V.4
- **20/20 passing**
- ~30 seconds total runtime (8s without `@slow`)
- Layers V.5 and V.6 remain TODO (gated on A.10 and A.13 implementations)

## V.1 — Cross-check vs `hmmlearn` baseline

**Goal** : on an ergodic topology without structural mask, our `fit()`
dispatcher must produce strictly the same parameters as `hmmlearn` ran
directly with the same initial conditions. If V.1 fails, there's a bug
in our glue code (init dispatch, parameter setting, mask application).

**Why ergodic and no mask** : on this configuration our backend delegates
fully to `hmmlearn`. Any difference can only come from a wiring bug.

**Tolerance** :
- Parameter arrays (transmat, startprob, means, covars, weights, emissionprob, lambdas) : `atol=1e-12`
- Log-likelihood : `rtol=1e-12` (relative tolerance — `model.score(X)`
  involves summations whose order may differ slightly between two
  identical models due to BLAS scheduling, giving O(1e-12) relative
  noise even when parameters are byte-identical)

We're not validating the EM algorithm, we're validating that our glue
code does not perturb it.

### Tests

| ID | Emission | Init strategy | Notes |
|---|---|---|---|
| V.1.1 | Gaussian (diag) | uniform | Most common case |
| V.1.2 | GMM (2-mix, diag) | random | Most error-prone (more params) |
| V.1.3 | Multinomial (4 symbols) | uniform | Discrete observations |
| V.1.4 | Poisson | uniform | Count data |

## Methodology

For each test :
1. Generate fixed synthetic data with a seeded `np.random.Generator`.
2. Build a `Topology` with `allowed_transitions=None` (ergodic).
3. Use our pipeline to compute initial parameters (transmat, startprob,
   emission overrides) — these are pre-EM.
4. Run our `fit()` → record final parameters.
5. Instantiate the corresponding raw `hmmlearn` class, **set the same
   initial parameters**, disable hmmlearn's auto-init (`init_params=""`),
   run `.fit()` → record final parameters.
6. Assert numerical agreement on `transmat_`, `startprob_`, emission
   parameters, and `score(X)`, to 1e-12.

## What V.1 does NOT test

- Numerical correctness of `hmmlearn` itself (we treat it as the reference)
- Constrained topology behavior (V.2 / V.3 / unit tests cover this)
- Init strategy quality (orthogonal concern)
- Edge cases (V.4)

## Reproducibility

All seeds are fixed in `conftest.py` (`rng_seed = 42`). Outputs should be
deterministic across Python and hmmlearn versions, except in case of
upstream hmmlearn behavior change — that's exactly the regression V.1 is
designed to catch.
