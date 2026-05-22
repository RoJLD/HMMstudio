"""V.perf — Performance regression suite.

These tests measure wall-clock fit time on representative (K, T) configurations
and assert that they stay under a budget. They are gated by both
``@pytest.mark.validation`` and ``@pytest.mark.perf`` so they can be skipped or
selected:

    pytest validation/ -m perf -v           # only the perf tests
    pytest validation/ -m validation -v     # all validation, including perf

Budgets are intentionally generous (chosen to be ~2x the median measured on a
modest dev machine). If a future change is slow enough to trip these, that's
a real regression worth investigating.

Method:
- Fixed random seed for the synthetic data → reproducible measurements
- Repeated execution (median of 3) to reduce single-run noise
- Each test compares to a hard upper bound; we don't try to do statistical
  regression detection — that's overkill for our scale.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from hmm_core import fit as core_fit, fit_nhmm
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


pytestmark = [pytest.mark.validation, pytest.mark.perf]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _gen_gaussian(K: int, T: int, n_features: int = 2, seed: int = 0) -> np.ndarray:
    """Deterministic synthetic Gaussian-HMM data."""
    rng = np.random.default_rng(seed)
    # Build a sane A: mostly diagonal so the model has structure to find
    A = 0.7 * np.eye(K) + 0.3 / K
    # Means well-separated along feature 0
    means = np.zeros((K, n_features))
    for k in range(K):
        means[k, 0] = (k - (K - 1) / 2.0) * 2.5
    cov = 0.3 * np.eye(n_features)
    state = 0
    X = np.zeros((T, n_features))
    for t in range(T):
        X[t] = rng.multivariate_normal(means[state], cov)
        state = int(rng.choice(K, p=A[state]))
    return X


def _gaussian_topo(K: int, n_features: int = 2, init: str = "kmeans") -> Topology:
    return Topology(
        name=f"perf_K{K}",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", n_features=n_features, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy=init, seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-4),
    )


def _median_fit_time(X: np.ndarray, topo: Topology, repeats: int = 3) -> float:
    """Run ``fit()`` ``repeats`` times, return the median wall-clock duration in seconds."""
    durations: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        core_fit(topo, X)
        durations.append(time.perf_counter() - t0)
    durations.sort()
    return durations[len(durations) // 2]


# ----------------------------------------------------------------------------
# Test budgets — chosen to be ~2x median on a modest dev machine
# ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "K, T, budget_s",
    [
        pytest.param(3, 500, 2.0, id="small_K3_T500"),
        pytest.param(5, 2000, 5.0, id="medium_K5_T2000"),
        pytest.param(10, 5000, 15.0, id="large_K10_T5000"),
        # K=20 is on the boundary of what hmmlearn handles efficiently — generous budget
        pytest.param(20, 5000, 30.0, id="xlarge_K20_T5000"),
    ],
)
def test_perf_gaussian_fit(K: int, T: int, budget_s: float):
    """Gaussian HMM fit stays under budget."""
    X = _gen_gaussian(K=K, T=T)
    topo = _gaussian_topo(K=K)
    duration = _median_fit_time(X, topo, repeats=3)
    assert duration < budget_s, (
        f"Gaussian fit K={K} T={T} took {duration:.2f}s (median of 3), "
        f"budget {budget_s}s. Investigate regression."
    )


# ----------------------------------------------------------------------------
# NHMM performance — covariate-driven transitions add a logistic regression
# stage; this checks that overhead is bounded
# ----------------------------------------------------------------------------

def test_perf_nhmm_fit():
    """NHMM fit (K=3, T=2000, P=2 covariates) stays under budget."""
    K = 3
    T = 2000
    rng = np.random.default_rng(42)
    Z = rng.normal(size=(T, 2))
    X = _gen_gaussian(K=K, T=T)

    topo = _gaussian_topo(K=K)
    durations: list[float] = []
    for _ in range(3):
        t0 = time.perf_counter()
        fit_nhmm(topo, X, Z, covariate_names=["z0", "z1"], seed=42)
        durations.append(time.perf_counter() - t0)
    durations.sort()
    median = durations[len(durations) // 2]
    assert median < 8.0, (
        f"NHMM fit K={K} T={T} took {median:.2f}s (median of 3), "
        f"budget 8.0s. Investigate regression."
    )


# ----------------------------------------------------------------------------
# Comparison: with-prior vs without-prior should be ~same cost
# ----------------------------------------------------------------------------

def test_perf_prior_overhead_bounded():
    """Adding a Dirichlet prior should add < 50% overhead to a fit."""
    K, T = 5, 2000
    X = _gen_gaussian(K=K, T=T)

    # Without prior
    topo_no_prior = _gaussian_topo(K=K)
    t_no_prior = _median_fit_time(X, topo_no_prior, repeats=3)

    # With prior
    topo_with_prior = Topology(
        name="perf_prior",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-4),
        transmat_prior_alpha=2.0,
    )
    t_with_prior = _median_fit_time(X, topo_with_prior, repeats=3)

    overhead_ratio = t_with_prior / max(t_no_prior, 1e-6)
    assert overhead_ratio < 1.5, (
        f"Dirichlet prior added {(overhead_ratio - 1) * 100:.1f}% overhead "
        f"(no_prior={t_no_prior:.3f}s, with_prior={t_with_prior:.3f}s). "
        f"Budget: < 50% overhead. Investigate _map_update cost."
    )
