"""V.4 — Numerical stability stress tests.

We deliberately push the fit pipeline into difficult regimes and check that
it does NOT silently produce garbage. Each test asserts :
    1. The fit completes without raising (unless explicit error)
    2. The log-likelihood is finite (no NaN/Inf)
    3. Probabilistic invariants are preserved (transmat rows sum to 1, etc.)
    4. The output is at least *qualitatively* useful (when applicable)

These tests do NOT validate that the fit is statistically optimal — only
that it remains numerically sane under stress.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


# ---------------------------------------------------------------------------
# V.4.1 — Long sequence (T = 100k) : log-space underflow protection
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_v4_1_long_sequence_no_underflow(rng_seed):
    """T = 100k Gaussian sequence : log-likelihood must be finite and fit must complete < 60s.

    Linear-space forward-backward would underflow disastrously at T ≈ 10^3.
    Log-space implementation (hmmlearn standard) handles 10^5 trivially —
    this test pins that the chain stays in log-space all the way through.
    """
    rng = np.random.default_rng(rng_seed)
    T = 100_000
    K = 3
    X = np.concatenate(
        [
            rng.normal(0.0, 1.0, (T // 3, 1)),
            rng.normal(5.0, 1.0, (T // 3, 1)),
            rng.normal(-3.0, 1.0, (T - 2 * (T // 3), 1)),
        ]
    )

    topo = Topology(
        name="v4-1-long",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )

    t0 = time.perf_counter()
    result = fit(topo, X, seed=rng_seed)
    elapsed = time.perf_counter() - t0

    assert np.isfinite(result.log_likelihood), (
        f"log-likelihood non-finite : {result.log_likelihood}"
    )
    assert elapsed < 60.0, f"fit on T={T} took {elapsed:.1f}s, expected < 60s"
    # Probabilistic invariants
    assert np.allclose(result.model.transmat_.sum(axis=1), 1.0, atol=1e-9)
    assert np.allclose(result.model.startprob_.sum(), 1.0, atol=1e-9)


# ---------------------------------------------------------------------------
# V.4.2 — Near-singular covariance (regularization must kick in)
# ---------------------------------------------------------------------------


def test_v4_2_near_singular_covariance_regularized(rng_seed):
    """Data nearly collinear in 2D : covariance regularization must keep fit finite.

    Without regularization, fitting full-cov Gaussian on rank-deficient data
    produces NaN log-likelihood at the first M-step. Our init module adds
    1e-3 · I to empirical covariances ; verify this prevents the breakdown.
    """
    rng = np.random.default_rng(rng_seed)
    T = 500

    # 3 quasi-1D clusters embedded in 2D (rank deficient by construction)
    direction = np.array([1.0, 1.0]) / np.sqrt(2)
    X_parts = []
    for center in [-5.0, 0.0, 5.0]:
        t = rng.normal(center, 1.0, T // 3)
        cluster = t[:, None] * direction[None, :] + rng.normal(0, 0.005, (T // 3, 2))
        X_parts.append(cluster)
    X = np.concatenate(X_parts)

    topo = Topology(
        name="v4-2-singular",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", covariance_type="full", n_features=2),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-5),
    )
    result = fit(topo, X, seed=rng_seed)

    assert np.isfinite(result.log_likelihood)
    # Each per-state covariance must be positive definite (smallest eigenvalue > 0)
    for k in range(3):
        eigs = np.linalg.eigvalsh(result.model.covars_[k])
        assert eigs.min() > 1e-10, (
            f"state {k} covariance eigvals = {eigs} (smallest must be > 0 after regularization)"
        )


# ---------------------------------------------------------------------------
# V.4.3 — Rare state (visited ≪ T) : MLE still sane
# ---------------------------------------------------------------------------


def test_v4_3_rare_state_does_not_break_fit(rng_seed):
    """A state visited only a handful of times must not crash the fit."""
    rng = np.random.default_rng(rng_seed)
    T = 10_000
    # Build a sequence where state 2 only appears in a single short burst
    X = np.concatenate(
        [
            rng.normal(0.0, 1.0, (4500, 1)),     # state 0
            rng.normal(20.0, 0.5, (10, 1)),       # state 2 : rare burst, n=10
            rng.normal(5.0, 1.0, (5490, 1)),     # state 1
        ]
    )

    topo = Topology(
        name="v4-3-rare",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-5),
    )

    result = fit(topo, X, seed=rng_seed)

    assert np.isfinite(result.log_likelihood)
    # All states must have valid means and positive variances
    means = np.asarray(result.model.means_).ravel()
    covars = np.asarray(result.model.covars_).ravel()
    assert np.all(np.isfinite(means))
    assert np.all(covars > 0)
    # The rare burst should be findable in one of the states (mean near 20)
    assert means.max() > 15.0, (
        f"rare burst at μ≈20 not captured by any state. Means : {means}"
    )


# ---------------------------------------------------------------------------
# V.4.4 — Large K (left-right K=15) : constrained fit at scale
# ---------------------------------------------------------------------------


def test_v4_4_large_K_left_right_respects_mask(rng_seed):
    """15-state left-right : fit completes, mask is respected, log-lik finite.

    Mostly a smoke test for K large. With K=15 left-right and well-separated
    means, EM should find a reasonable solution. We don't test parameter
    recovery (would need much longer sequences) — only that nothing breaks.
    """
    rng = np.random.default_rng(rng_seed)
    K = 15
    T = 5000

    # Each state has its own well-separated mean
    means_true = np.arange(K, dtype=float) * 3.0
    state_visits = rng.choice(K, size=T, replace=True)
    X = np.array([rng.normal(means_true[s], 0.5) for s in state_visits]).reshape(-1, 1)

    allowed = [
        [f"s{i}", f"s{j}"] for i in range(K) for j in range(K) if j in (i, i + 1)
    ]
    topo = Topology(
        name="v4-4-largeK",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=allowed,
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-4),
    )

    result = fit(topo, X, seed=rng_seed)

    assert np.isfinite(result.log_likelihood)
    # Mask invariant : forbidden edges are exactly zero
    forbidden = ~topo.transition_mask()
    assert np.all(np.asarray(result.model.transmat_)[forbidden] == 0.0)
    # All rows sum to 1
    assert np.allclose(result.model.transmat_.sum(axis=1), 1.0, atol=1e-9)


# ---------------------------------------------------------------------------
# V.4.5 — Empty data column (degenerate input) : explicit error, not silent garbage
# ---------------------------------------------------------------------------


def test_v4_5_constant_data_does_not_silently_produce_garbage(rng_seed):
    """Constant observation column has zero variance → emission fit must handle it.

    Either by (a) regularizing the covariance ≥ floor, or (b) raising an
    explicit error pointing at the constant column. We tolerate either, but
    refuse silent NaN or Inf outputs.
    """
    T = 500
    X = np.zeros((T, 1))  # all-zero constant column

    topo = Topology(
        name="v4-5-constant",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-4),
    )

    try:
        result = fit(topo, X, seed=rng_seed)
    except (ValueError, RuntimeError) as e:
        # Explicit failure is acceptable behavior — surface it loudly
        # (the caller knows the data is degenerate).
        msg = str(e).lower()
        # Just verify the error mentions something meaningful (not a cryptic numpy crash)
        assert any(w in msg for w in ("variance", "constant", "degenerate", "singular", "zero")), (
            f"degenerate-input error message too cryptic : {e}"
        )
        return

    # If the fit completed, results must NOT contain NaN or Inf
    assert np.isfinite(result.log_likelihood), (
        f"silent NaN/Inf log-likelihood on constant data : {result.log_likelihood}"
    )
    assert np.all(np.isfinite(result.model.means_))
    assert np.all(np.isfinite(result.model.covars_))
    assert np.all(np.asarray(result.model.covars_) > 0)
