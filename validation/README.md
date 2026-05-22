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
| **V.5** | Cross-check A.10 GMM-NHMM Strategy A vs raw oracles | ✅ **SHIPPED** (2026-05-22) | 5/5 passing | Independent hmmlearn + sklearn oracles + synthetic recovery |
| **V.6** | Cross-check A.13 Factorial NHMM Strategy A vs raw oracles | ✅ **SHIPPED** (2026-05-22) | 5/5 passing | Independent hmmlearn + sklearn oracles + recovery + param-count savings (27× at D=3 K=3) |
| **V.perf** | Performance regression (wall-clock budgets on representative K/T) | ✅ **SHIPPED** (2026-05-22) | 6/6 passing | Median of 3 runs vs hard budget; `@pytest.mark.perf` |

## Quick stats (2026-05-22 PM v3 — post A.10 + A.13 ship)

- **36 tests** total across V.1, V.2, V.3, V.4, V.5, V.6, V.perf
- **36/36 passing**
- ~50 seconds total runtime (~22s without `@slow`)
- **All planned layers shipped.** Future layers (V.7+) would be added for
  new model variants (e.g. A.11 HHMM, A.6 Bayesian backend).

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

## V.perf — Performance regression (`pytest.mark.perf`)

Wall-clock budgets for representative `(K, T)` Gaussian fits + NHMM + with/without prior overhead. These are NOT correctness tests — they detect if a change accidentally slows down EM significantly.

| Test | K | T | Budget |
|---|---|---|---|
| `test_perf_gaussian_fit[small_K3_T500]` | 3 | 500 | 2 s |
| `test_perf_gaussian_fit[medium_K5_T2000]` | 5 | 2000 | 5 s |
| `test_perf_gaussian_fit[large_K10_T5000]` | 10 | 5000 | 15 s |
| `test_perf_gaussian_fit[xlarge_K20_T5000]` | 20 | 5000 | 30 s |
| `test_perf_nhmm_fit` | 3 | 2000 | 8 s |
| `test_perf_prior_overhead_bounded` | 5 | 2000 | 50% overhead max |

Median of 3 runs is compared to the budget. Budgets are intentionally generous (~2× median on a modest dev machine) — they catch order-of-magnitude regressions, not micro-pessimizations.

Run only the perf tests:

```bash
pytest validation/ -m perf -v
```
