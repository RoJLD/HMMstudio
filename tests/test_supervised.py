"""Tests for supervised HMM fit (Phase A.7).

Supervised mode = the state sequence is observed during training, so MLE
becomes closed-form (count transitions, count emissions per state). No EM
iteration needed.
"""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.backends import HmmlearnBackend, get_backend
from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _gaussian_topo(K: int = 3, cov: str = "diag", allowed=None) -> Topology:
    return Topology(
        name="sup-gauss",
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
        name="sup-mult",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="multinomial", n_symbols=n_symbols),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )


def _poisson_topo(K: int = 2) -> Topology:
    return Topology(
        name="sup-poisson",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="poisson", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )


def _well_separated_data(states: np.ndarray, seed: int = 0) -> np.ndarray:
    """Make Gaussian observations that are trivially separable by state index."""
    rng = np.random.default_rng(seed)
    centers = {k: 5.0 * k for k in np.unique(states)}
    X = np.array([rng.normal(centers[s], 0.3) for s in states]).reshape(-1, 1)
    return X


# ---------------------------------------------------------------------------
# Public API : states= parameter
# ---------------------------------------------------------------------------


def test_supervised_converges_in_one_pass_gaussian():
    topo = _gaussian_topo(K=3)
    states = np.array([0, 0, 1, 1, 1, 2, 2, 0, 1, 2, 2, 2])
    X = _well_separated_data(states)
    result = fit(topo, X, states=states)
    assert result.n_iter_actual == 1
    assert result.converged is True


def test_supervised_transmat_matches_count_matrix():
    """The fitted transmat must equal normalized empirical transition counts."""
    topo = _gaussian_topo(K=3)
    states = np.array([0, 1, 1, 2, 0, 1, 2, 2, 0, 1])
    X = _well_separated_data(states)
    result = fit(topo, X, states=states)

    # Expected counts:
    # 0->1: 3 times (positions 0,4,8)
    # 1->1: 1 (1->1 at pos 1)
    # 1->2: 3 (positions 2,5,9... wait let me recount)
    K = 3
    expected = np.zeros((K, K))
    for t in range(len(states) - 1):
        expected[states[t], states[t + 1]] += 1
    expected /= expected.sum(axis=1, keepdims=True)

    assert np.allclose(result.model.transmat_, expected, atol=1e-6)


def test_supervised_respects_topology_mask_when_compatible():
    """A left-right topology where the labels don't violate the mask."""
    allowed = [["s0", "s0"], ["s0", "s1"], ["s1", "s1"], ["s1", "s2"], ["s2", "s2"]]
    topo = _gaussian_topo(K=3, allowed=allowed)
    states = np.array([0, 0, 1, 1, 1, 2, 2, 2])  # only allowed transitions
    X = _well_separated_data(states)
    result = fit(topo, X, states=states)

    # Forbidden edges must be exactly zero.
    forbidden = ~topo.transition_mask()
    assert np.all(result.model.transmat_[forbidden] == 0.0)
    # Allowed rows sum to 1.
    assert np.allclose(result.model.transmat_.sum(axis=1), 1.0)


def test_supervised_raises_when_labels_violate_mask():
    """If the labeled sequence contains a transition that the topology forbids,
    surface an explicit error instead of silently masking it away."""
    allowed = [["s0", "s0"], ["s0", "s1"], ["s1", "s1"], ["s1", "s2"], ["s2", "s2"]]
    topo = _gaussian_topo(K=3, allowed=allowed)
    states = np.array([0, 1, 2, 1, 0])  # 2->1 and 1->0 are forbidden
    X = _well_separated_data(states)
    with pytest.raises(ValueError, match="forbidden|mask"):
        fit(topo, X, states=states)


def test_supervised_emission_means_recovered():
    """For well-separated Gaussian data, supervised means must lie close to the
    true centers used to generate the data."""
    topo = _gaussian_topo(K=3)
    states = np.repeat([0, 1, 2], 50)
    X = _well_separated_data(states, seed=1)
    result = fit(topo, X, states=states)
    means = np.asarray(result.model.means_).ravel()
    # Sorted to remove permutation noise (here states are aligned, so identity).
    assert means[0] == pytest.approx(0.0, abs=0.1)
    assert means[1] == pytest.approx(5.0, abs=0.1)
    assert means[2] == pytest.approx(10.0, abs=0.1)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_supervised_rejects_states_with_wrong_length():
    topo = _gaussian_topo(K=2)
    X = np.array([[0.0], [1.0], [2.0]])
    states = np.array([0, 1])  # length 2 vs X length 3
    with pytest.raises(ValueError, match="length|shape"):
        fit(topo, X, states=states)


def test_supervised_rejects_states_out_of_range():
    topo = _gaussian_topo(K=2)
    X = np.array([[0.0], [1.0], [2.0]])
    states = np.array([0, 1, 5])  # 5 >= K=2
    with pytest.raises(ValueError, match="out of range|out-of-range|n_states|valid"):
        fit(topo, X, states=states)


def test_semisupervised_dispatches_to_em_when_labels_missing():
    """Partial labels (NaN entries) trigger semi-supervised EM (Phase A.7.1).

    No NotImplementedError is raised any more — the backend runs a
    constrained Baum-Welch with the E-step clamped at labelled positions.
    """
    topo = _gaussian_topo(K=2)
    X = _well_separated_data(np.array([0, 0, 1, 1, 0, 1, 0, 1]))
    states = np.array([0.0, np.nan, 1.0, np.nan, np.nan, 1.0, 0.0, np.nan])
    result = fit(topo, X, states=states)
    # Semi-supervised path runs EM, so converged + n_iter_actual >= 1.
    assert result.n_iter_actual >= 1
    assert np.isfinite(result.log_likelihood)


# ---------------------------------------------------------------------------
# Per-emission supervised paths
# ---------------------------------------------------------------------------


def test_supervised_multinomial_emissionprob_matches_counts():
    topo = _multinomial_topo(K=2, n_symbols=3)
    # State 0 emits mostly symbol 0; state 1 emits mostly symbol 2.
    states = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    X = np.array([0, 0, 0, 1, 2, 2, 2, 1]).reshape(-1, 1)
    result = fit(topo, X, states=states)
    ep = np.asarray(result.model.emissionprob_)
    # State 0: 3/4 of symbol 0, 1/4 of symbol 1.
    assert ep[0, 0] == pytest.approx(0.75, abs=1e-3)
    assert ep[0, 1] == pytest.approx(0.25, abs=1e-3)
    # State 1: 3/4 of symbol 2, 1/4 of symbol 1.
    assert ep[1, 1] == pytest.approx(0.25, abs=1e-3)
    assert ep[1, 2] == pytest.approx(0.75, abs=1e-3)


def test_supervised_poisson_lambdas_match_per_state_means():
    topo = _poisson_topo(K=2)
    states = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    X = np.array([2, 3, 2, 3, 10, 11, 10, 11]).reshape(-1, 1).astype(float)
    result = fit(topo, X, states=states)
    lambdas = np.asarray(result.model.lambdas_).ravel()
    assert lambdas[0] == pytest.approx(2.5, abs=1e-6)
    assert lambdas[1] == pytest.approx(10.5, abs=1e-6)


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


def test_hmmlearn_backend_exposes_fit_supervised():
    backend = get_backend("hmmlearn")
    assert hasattr(backend, "fit_supervised")
    assert callable(backend.fit_supervised)


def test_backend_fit_supervised_returns_BackendFitResult():
    from hmm_core.backends import BackendFitResult

    backend = HmmlearnBackend()
    topo = _gaussian_topo(K=2)
    states = np.array([0, 0, 1, 1])
    X = _well_separated_data(states)
    mask = topo.transition_mask()
    result = backend.fit_supervised(topo, X, states, seed=0, lengths=None, mask=mask)
    assert isinstance(result, BackendFitResult)
    assert result.n_iter_actual == 1
    assert result.converged is True


# ---------------------------------------------------------------------------
# Lengths support (multi-sequence supervised fit)
# ---------------------------------------------------------------------------


def test_supervised_gmm_now_supported_after_a71():
    """GMM supervised was punted to A.7.1; it now fits per-state GaussianMixture.

    Smoke test: should not raise NotImplementedError, should return a usable
    model with finite log-likelihood.
    """
    topo = Topology(
        name="sup-gmm",
        n_states=2,
        state_names=["s0", "s1"],
        emission=EmissionSpec(type="gmm", covariance_type="diag", n_features=1, n_mix=2),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )
    states = np.repeat([0, 1], 30)
    X = _well_separated_data(states)
    result = fit(topo, X, states=states)
    assert result.n_iter_actual == 1
    assert np.isfinite(result.log_likelihood)


def test_supervised_rejects_negative_state_label_below_minus_one():
    """Negative state values (other than the -1 semi-supervised sentinel) are out of range.

    -1 is now reserved (semi-supervised sentinel for int arrays), but -2 and
    below remain plain invalid labels.
    """
    topo = _gaussian_topo(K=2)
    X = np.array([[0.0], [1.0], [2.0], [3.0]])
    states = np.array([0, -2, 1, 0])
    with pytest.raises(ValueError, match="range|valid|n_states"):
        fit(topo, X, states=states)


def test_supervised_int_minus_one_dispatches_to_semi_supervised():
    """Int array with -1 entries triggers semi-supervised EM (not a range error)."""
    topo = _gaussian_topo(K=2)
    states_true = np.array([0, 0, 1, 1, 0, 1])
    X = _well_separated_data(states_true)
    states = np.array([0, -1, 1, -1, -1, 1])
    result = fit(topo, X, states=states)
    assert np.isfinite(result.log_likelihood)


def test_protocol_declares_progress_callback():
    """Regression: the HMMBackend protocol must declare progress_callback so
    third-party backends know they need to accept it (or **kwargs)."""
    import inspect

    from hmm_core.backends import HMMBackend

    sig = inspect.signature(HMMBackend.fit)
    assert "progress_callback" in sig.parameters, (
        "HMMBackend.fit must declare progress_callback in its protocol signature, "
        "otherwise third-party backends will TypeError when fit() forwards it"
    )


def test_supervised_with_lengths_no_cross_sequence_transition():
    """Boundary transitions between concatenated sequences must NOT be counted."""
    topo = _gaussian_topo(K=2)
    # Two sequences: [0,0,1] and [1,0,0]. If we naively concatenated and counted
    # transitions, we'd register a 1->1 between them. With lengths, we don't.
    states = np.array([0, 0, 1, 1, 0, 0])
    X = _well_separated_data(states)
    lengths = np.array([3, 3])

    result = fit(topo, X, states=states, lengths=lengths)

    # Expected counts within each sequence only:
    # seq 1: 0->0, 0->1.   seq 2: 1->0, 0->0.
    # row 0: 0->0 count = 2 (one per seq), 0->1 count = 1.  Total row 0 = 3.
    # row 1: 1->0 count = 1, 1->1 = 0.                       Total row 1 = 1.
    expected = np.array([[2.0 / 3.0, 1.0 / 3.0], [1.0, 0.0]])
    assert np.allclose(result.model.transmat_, expected, atol=1e-6)


# ---------------------------------------------------------------------------
# GMM supervised (Phase A.7.1)
# ---------------------------------------------------------------------------


def _gmm_topo(K: int = 3, n_mix: int = 2, n_features: int = 2, cov: str = "diag") -> Topology:
    return Topology(
        name="sup-gmm",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gmm", covariance_type=cov, n_features=n_features, n_mix=n_mix),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )


def _gmm_well_separated(K: int, n_mix: int, n_per: int, seed: int = 0):
    """Generate GMM-distributed data with per-state, per-mixture means well separated.

    Returns (X, states, true_means_per_state).
    """
    rng = np.random.default_rng(seed)
    # State k's mixtures live around (10*k, 10*k) and (10*k+3, 10*k+3) — far
    # from any other state's modes.
    true_means = np.zeros((K, n_mix, 2))
    for k in range(K):
        for m in range(n_mix):
            true_means[k, m] = [10.0 * k + 3.0 * m, 10.0 * k + 3.0 * m]
    states_list = []
    X_list = []
    for k in range(K):
        for _ in range(n_per):
            m = int(rng.integers(0, n_mix))
            X_list.append(rng.multivariate_normal(true_means[k, m], 0.2 * np.eye(2)))
            states_list.append(k)
    return np.array(X_list), np.array(states_list), true_means


def test_gmm_supervised_recovers_means():
    """K=3, M=2, well-separated sub-modes — recovered means within 0.3 of truth."""
    K, M = 3, 2
    X, states, true_means = _gmm_well_separated(K, M, n_per=80, seed=11)
    topo = _gmm_topo(K=K, n_mix=M, n_features=2, cov="diag")
    result = fit(topo, X, states=states)
    means = np.asarray(result.model.means_)  # (K, M, D)
    # For each state, allow permutation of mixture components.
    for k in range(K):
        # Sort by first feature to align with sorted truth.
        rec_sorted = means[k][np.argsort(means[k][:, 0])]
        true_sorted = true_means[k][np.argsort(true_means[k][:, 0])]
        assert np.allclose(rec_sorted, true_sorted, atol=0.3), (
            f"state {k}: recovered {rec_sorted} vs true {true_sorted}"
        )


def test_gmm_supervised_handles_degenerate_state():
    """A state with < M observations falls back to uniform weights, no crash."""
    K, M = 2, 3  # 3 mixtures per state but state 1 only gets 2 observations
    topo = _gmm_topo(K=K, n_mix=M, n_features=2, cov="diag")
    # State 0 gets lots of points, state 1 only gets 2 (< M=3).
    X = np.vstack(
        [
            np.random.RandomState(0).randn(50, 2),
            np.array([[10.0, 10.0], [11.0, 11.0]]),
        ]
    )
    states = np.concatenate([np.zeros(50, dtype=int), np.ones(2, dtype=int)])
    result = fit(topo, X, states=states)
    weights = np.asarray(result.model.weights_)  # (K, M)
    # State 1 should have uniform weights (the fallback path).
    assert np.allclose(weights[1], 1.0 / M, atol=1e-6)


def test_gmm_supervised_log_likelihood_is_finite():
    """Sanity: model.score returns finite, and predict works after supervised fit."""
    K, M = 3, 2
    X, states, _ = _gmm_well_separated(K, M, n_per=40, seed=3)
    topo = _gmm_topo(K=K, n_mix=M, n_features=2, cov="diag")
    result = fit(topo, X, states=states)
    assert np.isfinite(result.log_likelihood)
    # Model is usable for downstream prediction.
    pred = result.model.predict(X)
    assert pred.shape == (len(X),)
    assert pred.min() >= 0 and pred.max() < K
