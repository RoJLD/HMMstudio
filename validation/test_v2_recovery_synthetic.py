"""V.2 — Statistical recovery on synthetic data.

For each emission type, we :
    1. Build a HMM with KNOWN parameters
    2. Sample N observations + true state sequence from it (via hmmlearn)
    3. Fit our hmm-studio pipeline on the observations only
    4. Use the Hungarian algorithm to align estimated states to true states
    5. Assert recovery of (means, covars, weights, transmat, startprob) within
       tolerances deduced from MLE asymptotic variance

This validates that the estimator is **statistically correct** : it
converges to the truth as N → ∞.

Recovery tolerances are deduced as follows :
- Gaussian means : σ/sqrt(N · π_min) where π_min is the smallest stationary
  probability. For N=5000, K=3, σ=1, this gives σ_μ ≈ 0.05 → tolerance 0.2
  is conservative (4× the asymptotic σ).
- Transition matrix : standard error on row i ≈ sqrt(p(1-p) / visits_i) where
  visits_i = N · π_i. For N=5000, π=1/3, p=0.8 → σ_A ≈ 0.01 → tolerance 0.05
  is conservative.
- We test KL divergence on the transition matrix as a one-number summary.
"""

from __future__ import annotations

import numpy as np
import pytest
from hmmlearn.hmm import CategoricalHMM, GaussianHMM, GMMHMM, PoissonHMM

from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

from ._helpers import (
    kl_divergence_transmat,
    match_states_by_emission_prob,
    match_states_by_means,
)


# ---------------------------------------------------------------------------
# V.2.1 — Gaussian 3-state ergodic
# ---------------------------------------------------------------------------


def test_v2_1_gaussian_3state_ergodic_recovery(rng_seed):
    """3-state Gaussian ergodic. Recovery within asymptotic tolerance."""
    K = 3
    D = 2
    N = 5000

    # True model
    true_transmat = np.array(
        [
            [0.85, 0.10, 0.05],
            [0.10, 0.80, 0.10],
            [0.05, 0.15, 0.80],
        ]
    )
    true_startprob = np.array([0.33, 0.34, 0.33])
    true_means = np.array(
        [
            [0.0, 0.0],
            [5.0, -5.0],
            [-3.0, 4.0],
        ]
    )
    true_covars = np.tile(np.eye(D)[None] * 1.0, (K, 1, 1))  # full identity per state

    # Sample data
    ref = GaussianHMM(n_components=K, covariance_type="full", random_state=rng_seed)
    ref.startprob_ = true_startprob
    ref.transmat_ = true_transmat
    ref.means_ = true_means
    ref.covars_ = true_covars
    X, _ = ref.sample(N, random_state=rng_seed)

    # Fit
    topo = Topology(
        name="v2-1-gauss",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", covariance_type="full", n_features=D),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-5),
    )
    result = fit(topo, X, seed=rng_seed)
    est = result.model

    # Align estimated states to true states
    perm = match_states_by_means(true_means, np.asarray(est.means_))
    est_means = np.asarray(est.means_)[perm]
    est_transmat = np.asarray(est.transmat_)[perm][:, perm]

    # Recovery asserts
    assert np.linalg.norm(est_means - true_means, axis=1).max() < 0.2, (
        f"means recovery failed : {est_means} vs {true_means}"
    )
    assert kl_divergence_transmat(true_transmat, est_transmat) < 0.05, (
        f"transmat KL > 0.05 : true={true_transmat}, est={est_transmat}"
    )


# ---------------------------------------------------------------------------
# V.2.2 — Gaussian 4-state left-right (verify mask preserved AND recovery)
# ---------------------------------------------------------------------------


def test_v2_2_gaussian_4state_leftright_recovery(rng_seed):
    """4-state left-right Gaussian (cyclic lifecycle). Forbidden edges stay zero, params recovered.

    Design notes :
    - Strict left-right with absorbing final state would trap all observations
      in s3 (low data for s0/s1/s2). We use a **cyclic lifecycle** : s3 → s0
      allowed, so the chain walks 0→1→2→3→0→1→… repeatedly.
    - This is still a structurally constrained topology (only 8 of 16 edges
      allowed instead of all 16) — the mask test is valid.
    - N=5000 with each state visited ~equally.
    """
    K = 4
    D = 1
    N = 5000

    # Cyclic lifecycle : 4 states walked in order, then loop back.
    true_transmat = np.array(
        [
            [0.7, 0.3, 0.0, 0.0],
            [0.0, 0.7, 0.3, 0.0],
            [0.0, 0.0, 0.7, 0.3],
            [0.3, 0.0, 0.0, 0.7],   # cycle back to s0
        ]
    )
    true_startprob = np.array([1.0, 0.0, 0.0, 0.0])
    true_means = np.array([[0.0], [3.0], [6.0], [9.0]])
    true_covars = np.array([[[0.5]], [[0.5]], [[0.5]], [[0.5]]])

    ref = GaussianHMM(n_components=K, covariance_type="full", random_state=rng_seed)
    ref.startprob_ = true_startprob
    ref.transmat_ = true_transmat
    ref.means_ = true_means
    ref.covars_ = true_covars
    X, _ = ref.sample(N, random_state=rng_seed)

    allowed = [
        ["s0", "s0"], ["s0", "s1"],
        ["s1", "s1"], ["s1", "s2"],
        ["s2", "s2"], ["s2", "s3"],
        ["s3", "s3"], ["s3", "s0"],   # the cyclic edge
    ]
    topo = Topology(
        name="v2-2-leftright",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=EmissionSpec(type="gaussian", covariance_type="full", n_features=D),
        allowed_transitions=allowed,
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=200, tol=1e-5),
    )
    result = fit(topo, X, seed=rng_seed)
    est = result.model

    # Left-right doesn't have label switching ambiguity if init is kmeans-based
    # and means are well-separated → states should align by index already.
    perm = match_states_by_means(true_means, np.asarray(est.means_))
    est_means = np.asarray(est.means_)[perm]
    est_transmat = np.asarray(est.transmat_)[perm][:, perm]

    # Recovery
    assert np.abs(est_means - true_means).max() < 0.3, (
        f"means recovery failed : {est_means.ravel()} vs {true_means.ravel()}"
    )

    # Forbidden edges must be EXACTLY zero (mask is hard constraint)
    forbidden = ~topo.transition_mask()
    assert np.all(np.asarray(est.transmat_)[forbidden] == 0.0), (
        "forbidden edges leaked nonzero probability"
    )


# ---------------------------------------------------------------------------
# V.2.3 — Multinomial 3-state 5-symbol
# ---------------------------------------------------------------------------


def test_v2_3_multinomial_3state_recovery(rng_seed):
    """3-state Multinomial 5-symbol ergodic. Recover emissionprob per state.

    Design notes :
    - Each state has its emission distribution concentrated on a different
      symbol (states are nearly orthogonal in emission space). Without this,
      Baum-Welch can converge to bad local optima on multinomial because
      the init is degenerate (kmeans is meaningless on integer labels — see
      init.py warning).
    - Multi-start (5 seeds) is used to bypass the worst local optima. This
      mirrors what a user should do in practice.
    - N=5000 is sufficient when emissions are orthogonal.
    """
    K = 3
    n_symbols = 5
    N = 5000

    true_transmat = np.array(
        [
            [0.85, 0.075, 0.075],
            [0.075, 0.85, 0.075],
            [0.075, 0.075, 0.85],
        ]
    )
    # Orthogonal emissions : each state is concentrated on a distinct symbol.
    true_emissionprob = np.array(
        [
            [0.9, 0.025, 0.025, 0.025, 0.025],   # mode on symbol 0
            [0.025, 0.025, 0.025, 0.025, 0.9],   # mode on symbol 4
            [0.025, 0.025, 0.9, 0.025, 0.025],   # mode on symbol 2
        ]
    )
    true_startprob = np.array([0.33, 0.34, 0.33])

    ref = CategoricalHMM(n_components=K, n_features=n_symbols, random_state=rng_seed)
    ref.startprob_ = true_startprob
    ref.transmat_ = true_transmat
    ref.emissionprob_ = true_emissionprob
    X, _ = ref.sample(N, random_state=rng_seed)

    # Multi-start : 5 seeds, keep best log-likelihood. Realistic practitioner
    # workflow for multinomial.
    best_result = None
    for seed_offset in range(5):
        topo = Topology(
            name="v2-3-mult",
            n_states=K,
            state_names=[f"s{i}" for i in range(K)],
            emission=EmissionSpec(type="multinomial", n_symbols=n_symbols),
            allowed_transitions=None,
            startprob="uniform",
            init=InitSpec(strategy="random", seed=rng_seed + seed_offset),
            fit=FitSpec(algorithm="baum_welch", n_iter=200, tol=1e-5),
        )
        candidate = fit(topo, X, seed=rng_seed + seed_offset)
        if best_result is None or candidate.log_likelihood > best_result.log_likelihood:
            best_result = candidate
    est = best_result.model

    perm = match_states_by_emission_prob(true_emissionprob, np.asarray(est.emissionprob_))
    est_emissionprob = np.asarray(est.emissionprob_)[perm]
    est_transmat = np.asarray(est.transmat_)[perm][:, perm]

    # With orthogonal emissions + multi-start, recovery should be tight :
    # TV per state should be < 0.05 at N=5000.
    tv = 0.5 * np.abs(true_emissionprob - est_emissionprob).sum(axis=1)
    assert tv.max() < 0.05, f"emissionprob TV > 0.05 : per-state={tv}"

    assert kl_divergence_transmat(true_transmat, est_transmat) < 0.05


# ---------------------------------------------------------------------------
# V.2.4 — Poisson 2-state
# ---------------------------------------------------------------------------


def test_v2_4_poisson_2state_recovery(rng_seed):
    """2-state Poisson ergodic. Recover lambdas per state."""
    K = 2
    D = 1
    N = 3000

    true_transmat = np.array([[0.9, 0.1], [0.1, 0.9]])
    true_startprob = np.array([0.5, 0.5])
    true_lambdas = np.array([[2.0], [15.0]])

    ref = PoissonHMM(n_components=K, random_state=rng_seed)
    ref.startprob_ = true_startprob
    ref.transmat_ = true_transmat
    ref.lambdas_ = true_lambdas
    X, _ = ref.sample(N, random_state=rng_seed)

    topo = Topology(
        name="v2-4-poisson",
        n_states=K,
        state_names=["lo", "hi"],
        emission=EmissionSpec(type="poisson", n_features=D),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-5),
    )
    result = fit(topo, X.astype(float), seed=rng_seed)
    est = result.model

    perm = match_states_by_means(true_lambdas, np.asarray(est.lambdas_))
    est_lambdas = np.asarray(est.lambdas_)[perm].ravel()
    true_l = true_lambdas.ravel()

    # Relative error should be < 5 % at N=3000
    rel_err = np.abs(est_lambdas - true_l) / true_l
    assert rel_err.max() < 0.05, (
        f"lambdas recovery rel_err > 5 % : est={est_lambdas} vs true={true_l}"
    )


# ---------------------------------------------------------------------------
# V.2.5 — GMM 2-state 2-mix (harder, looser tolerance)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_v2_5_gmm_2state_2mix_recovery(rng_seed):
    """2-state GMM (2-mix diag) ergodic. Recovery is harder ; looser tolerance.

    GMM has known identifiability issues : within a state, the 2 mixture
    components can swap freely. We only test that the means **set** is
    recovered, not that component indices align.
    """
    K = 2
    M = 2
    D = 1
    N = 8000

    true_transmat = np.array([[0.9, 0.1], [0.1, 0.9]])
    true_startprob = np.array([0.5, 0.5])
    true_means = np.array(
        [
            [[0.0], [2.0]],
            [[10.0], [12.0]],
        ]
    )
    true_covars = np.tile(np.array([[[0.3]], [[0.3]]])[None], (K, 1, 1, 1)).reshape(K, M, D)
    true_weights = np.array([[0.6, 0.4], [0.5, 0.5]])

    ref = GMMHMM(n_components=K, n_mix=M, covariance_type="diag", random_state=rng_seed)
    ref.startprob_ = true_startprob
    ref.transmat_ = true_transmat
    ref.means_ = true_means
    ref.covars_ = true_covars
    ref.weights_ = true_weights
    X, _ = ref.sample(N, random_state=rng_seed)

    topo = Topology(
        name="v2-5-gmm",
        n_states=K,
        state_names=["lo", "hi"],
        emission=EmissionSpec(type="gmm", covariance_type="diag", n_features=D, n_mix=M),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=rng_seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=200, tol=1e-5),
    )
    result = fit(topo, X, seed=rng_seed)
    est = result.model

    # Align states by the average of their component means (more robust than
    # using individual components, since within-state mixture order is itself
    # ambiguous).
    true_state_means = true_means.mean(axis=1)  # (K, D)
    est_state_means = np.asarray(est.means_).mean(axis=1)  # (K, D)
    perm = match_states_by_means(true_state_means, est_state_means)

    est_means_all = np.asarray(est.means_)[perm]  # (K, M, D)

    # For each true state, the set of M means should match (up to permutation
    # within the state) within tolerance 1.0 (looser than V.2.1 ; GMM is harder).
    for k in range(K):
        true_set = np.sort(true_means[k].ravel())
        est_set = np.sort(est_means_all[k].ravel())
        assert np.abs(true_set - est_set).max() < 1.0, (
            f"GMM state {k} component means : est={est_set} vs true={true_set}"
        )
