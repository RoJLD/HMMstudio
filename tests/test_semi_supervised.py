"""Tests for semi-supervised HMM fit (Phase A.7.1).

Semi-supervised = some positions in the ``states`` array are unlabelled
(``NaN`` in a float array, or ``-1`` in an int array). The backend runs a
constrained Baum-Welch where the E-step is clamped to the known labels at
labelled positions and free at unlabelled positions. Initial parameters
come from the fully-supervised MLE on the labelled subset only.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment

from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gaussian_topo(K: int = 3, cov: str = "diag", allowed=None) -> Topology:
    return Topology(
        name="semi-gauss",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", covariance_type=cov, n_features=1),
        allowed_transitions=allowed,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )


def _multinomial_topo(K: int = 2, n_symbols: int = 4) -> Topology:
    return Topology(
        name="semi-mult",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="multinomial", n_symbols=n_symbols),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )


def _well_separated_gaussian(states: np.ndarray, seed: int = 0) -> np.ndarray:
    """Make 1-D Gaussian observations trivially separable by state index."""
    rng = np.random.default_rng(seed)
    centers = {k: 5.0 * k for k in np.unique(states)}
    X = np.array([rng.normal(centers[s], 0.3) for s in states]).reshape(-1, 1)
    return X


def _match_means_1d(true_means: np.ndarray, est_means: np.ndarray) -> np.ndarray:
    """Hungarian matching of estimated means to true means (1-D anchors)."""
    cost = np.abs(true_means[:, None] - est_means[None, :])
    _, col = linear_sum_assignment(cost)
    return col


def _make_labels(
    true_states: np.ndarray,
    fraction_labelled: float,
    seed: int,
    as_float: bool = True,
) -> np.ndarray:
    """Sample a fraction of true_states to keep; mark rest unlabelled.

    If as_float, returns a float array with NaN at unlabelled positions.
    Otherwise returns an int array with -1 at unlabelled positions.
    """
    rng = np.random.default_rng(seed)
    T = len(true_states)
    n_keep = max(1, int(round(fraction_labelled * T)))
    keep_idx = rng.choice(T, size=n_keep, replace=False)
    if as_float:
        labels = np.full(T, np.nan, dtype=float)
        labels[keep_idx] = true_states[keep_idx].astype(float)
    else:
        labels = np.full(T, -1, dtype=int)
        labels[keep_idx] = true_states[keep_idx].astype(int)
    return labels


def _simulate_gaussian(K: int, T: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simulate a simple persistent K-state Gaussian sequence.

    Returns (X, true_states, true_means).
    """
    rng = np.random.default_rng(seed)
    true_means = 5.0 * np.arange(K, dtype=float)
    # Persistent transitions (0.85 self, 0.15 split among others).
    A = np.full((K, K), 0.15 / max(K - 1, 1))
    np.fill_diagonal(A, 0.85)
    state = 0
    states = np.zeros(T, dtype=int)
    X = np.zeros((T, 1))
    for t in range(T):
        states[t] = state
        X[t, 0] = rng.normal(true_means[state], 0.3)
        state = int(rng.choice(K, p=A[state]))
    return X, states, true_means


# ---------------------------------------------------------------------------
# 1. All labels → result equivalent to fully-supervised
# ---------------------------------------------------------------------------


def test_semi_supervised_all_labels_matches_supervised():
    """When no positions are unlabelled, semi-supervised dispatch should NOT
    trigger — we hit the closed-form supervised path exactly as before.
    """
    topo = _gaussian_topo(K=3)
    true_states = np.array([0, 0, 1, 1, 1, 2, 2, 0, 1, 2, 2, 2])
    X = _well_separated_gaussian(true_states)

    # Reference: fully labelled int array → closed-form supervised.
    ref = fit(topo, X, states=true_states)
    # Float array, but every position labelled (no NaN). Should also take the
    # closed-form path (no NaN -> no -1 -> not semi-supervised).
    float_labels = true_states.astype(float)
    other = fit(topo, X, states=float_labels)

    assert other.n_iter_actual == ref.n_iter_actual == 1
    assert np.allclose(other.model.transmat_, ref.model.transmat_, atol=1e-10)
    assert np.allclose(other.model.means_, ref.model.means_, atol=1e-10)


# ---------------------------------------------------------------------------
# 2 & 3. Recovery with partial labels (Gaussian)
# ---------------------------------------------------------------------------


def test_semi_supervised_recovers_params_with_50pct_labels():
    """Gaussian K=3, 50% labelled → recovered means within 0.5 of truth."""
    K, T = 3, 300
    X, true_states, true_means = _simulate_gaussian(K, T, seed=7)
    labels = _make_labels(true_states, fraction_labelled=0.5, seed=7)
    topo = _gaussian_topo(K=K)

    result = fit(topo, X, states=labels)
    est_means = np.asarray(result.model.means_).ravel()
    perm = _match_means_1d(true_means, est_means)
    assert np.allclose(est_means[perm], true_means, atol=0.5)


def test_semi_supervised_recovers_params_with_10pct_labels():
    """Gaussian K=3, 10% labelled → recovered means within 0.8 of truth (loose)."""
    K, T = 3, 600
    X, true_states, true_means = _simulate_gaussian(K, T, seed=19)
    labels = _make_labels(true_states, fraction_labelled=0.1, seed=19)
    topo = _gaussian_topo(K=K)

    result = fit(topo, X, states=labels)
    est_means = np.asarray(result.model.means_).ravel()
    perm = _match_means_1d(true_means, est_means)
    assert np.allclose(est_means[perm], true_means, atol=0.8)


# ---------------------------------------------------------------------------
# 4. Multinomial works (different emission family)
# ---------------------------------------------------------------------------


def test_semi_supervised_multinomial_works():
    """Multinomial K=2, vocab=4, 30% labelled → emissionprob roughly recovered."""
    K, n_symbols, T = 2, 4, 400
    rng = np.random.default_rng(101)
    true_ep = np.array(
        [
            [0.7, 0.2, 0.05, 0.05],
            [0.05, 0.05, 0.2, 0.7],
        ]
    )
    A = np.array([[0.85, 0.15], [0.15, 0.85]])
    state = 0
    true_states = np.zeros(T, dtype=int)
    X = np.zeros((T, 1), dtype=int)
    for t in range(T):
        true_states[t] = state
        X[t, 0] = int(rng.choice(n_symbols, p=true_ep[state]))
        state = int(rng.choice(K, p=A[state]))

    labels = _make_labels(true_states, fraction_labelled=0.3, seed=2)
    topo = _multinomial_topo(K=K, n_symbols=n_symbols)
    result = fit(topo, X, states=labels)

    ep = np.asarray(result.model.emissionprob_)
    # Match states by emissionprob distance.
    cost = 0.5 * np.abs(true_ep[:, None, :] - ep[None, :, :]).sum(axis=-1)
    _, perm = linear_sum_assignment(cost)
    assert np.allclose(ep[perm], true_ep, atol=0.15)


# ---------------------------------------------------------------------------
# 5. Multi-sequence semi-supervised
# ---------------------------------------------------------------------------


def test_semi_supervised_with_lengths():
    """Multi-sequence semi-supervised — boundaries respected, no error."""
    K = 2
    seq1 = np.array([0, 0, 1, 1, 0])
    seq2 = np.array([1, 1, 0, 0, 1])
    true_states = np.concatenate([seq1, seq2])
    X = _well_separated_gaussian(true_states, seed=5)
    # Label half of each sequence (positions 0, 2, 4 of each).
    labels = np.full(len(true_states), np.nan, dtype=float)
    for offset in (0, 5):
        for j in (0, 2, 4):
            labels[offset + j] = float(true_states[offset + j])
    lengths = np.array([5, 5])
    topo = _gaussian_topo(K=K)

    result = fit(topo, X, states=labels, lengths=lengths)
    assert np.isfinite(result.log_likelihood)
    # Means are well-separated; the model should clearly identify s0 ≈ 0, s1 ≈ 5.
    means = np.sort(np.asarray(result.model.means_).ravel())
    assert means[0] == pytest.approx(0.0, abs=1.0)
    assert means[1] == pytest.approx(5.0, abs=1.0)


# ---------------------------------------------------------------------------
# 6. Forbidden labelled-labelled transitions raise
# ---------------------------------------------------------------------------


def test_semi_supervised_raises_on_labelled_forbidden_transition():
    """An observed transition between two adjacent labelled positions that
    violates the topology mask must surface as ValueError."""
    allowed = [["s0", "s0"], ["s0", "s1"], ["s1", "s1"], ["s1", "s2"], ["s2", "s2"]]
    topo = _gaussian_topo(K=3, allowed=allowed)
    # 2 -> 0 is a forbidden direct transition. Both positions are labelled.
    labels = np.array([2.0, 0.0, np.nan, 1.0, 1.0])
    X = _well_separated_gaussian(np.array([2, 0, 0, 1, 1]))
    with pytest.raises(ValueError, match="forbidden|mask"):
        fit(topo, X, states=labels)


# ---------------------------------------------------------------------------
# 7. Forbidden transition routed through an unlabelled position is OK
# ---------------------------------------------------------------------------


def test_semi_supervised_unlabelled_transition_through_forbidden_is_allowed():
    """Labels at t=0 and t=2 may differ by more than one step through the mask
    as long as t=1 is unlabelled — EM is free to route through the allowed
    intermediate state.
    """
    allowed = [["s0", "s0"], ["s0", "s1"], ["s1", "s1"], ["s1", "s2"], ["s2", "s2"]]
    topo = _gaussian_topo(K=3, allowed=allowed)
    # labels[0]=0, labels[2]=2 would be forbidden directly, but with
    # labels[1]=NaN the chain 0->1->2 is fine and EM should discover it.
    labels = np.array([0.0, np.nan, 2.0, 2.0, 2.0])
    X = _well_separated_gaussian(np.array([0, 1, 2, 2, 2]))
    # No exception expected.
    result = fit(topo, X, states=labels)
    assert np.isfinite(result.log_likelihood)


# ---------------------------------------------------------------------------
# 8. Int sentinel (-1) works identically to NaN float
# ---------------------------------------------------------------------------


def test_semi_supervised_int_sentinel_minus_one_also_works():
    """Passing int array with -1 sentinels must behave the same as float NaN."""
    K, T = 2, 60
    X, true_states, _ = _simulate_gaussian(K, T, seed=29)
    # Pick the same labelled positions for both representations.
    rng = np.random.default_rng(29)
    keep = rng.choice(T, size=int(0.4 * T), replace=False)

    labels_f = np.full(T, np.nan, dtype=float)
    labels_f[keep] = true_states[keep].astype(float)
    labels_i = np.full(T, -1, dtype=int)
    labels_i[keep] = true_states[keep].astype(int)

    topo = _gaussian_topo(K=K)
    res_f = fit(topo, X, states=labels_f)
    res_i = fit(topo, X, states=labels_i)

    # Two semi-supervised runs with the same labels and same seed should
    # produce the same fit.
    assert np.allclose(res_f.model.transmat_, res_i.model.transmat_, atol=1e-8)
    assert np.allclose(res_f.model.means_, res_i.model.means_, atol=1e-8)


# ---------------------------------------------------------------------------
# 9. All unlabelled → explicit error directing to unsupervised fit()
# ---------------------------------------------------------------------------


def test_semi_supervised_all_unlabelled_nan_raises():
    topo = _gaussian_topo(K=2)
    X = np.array([[0.0], [1.0], [2.0]])
    labels = np.array([np.nan, np.nan, np.nan])
    with pytest.raises(ValueError, match="no labelled|unsupervised|states=None"):
        fit(topo, X, states=labels)


def test_semi_supervised_all_unlabelled_minus_one_raises():
    topo = _gaussian_topo(K=2)
    X = np.array([[0.0], [1.0], [2.0]])
    labels = np.array([-1, -1, -1])
    with pytest.raises(ValueError, match="no labelled|unsupervised|states=None"):
        fit(topo, X, states=labels)
