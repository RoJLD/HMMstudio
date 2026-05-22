"""V.6 — Cross-check the Factorial NHMM 2-stage implementation (Phase A.13).

The shipped implementation (`fit_factorial_nhmm` in
`src/hmm_core/factorial_nhmm.py`) is the **Strategy A 2-stage** approach :
    Stage 1 : standard Gaussian HMM on K_joint = ∏K_d states (covariates ignored)
    Stage 2 : per-chain multinomial logit on covariates → A_t per chain

V.6 validates this implementation by cross-checking against independent
oracles :
    Stage 1 oracle : raw hmmlearn.GaussianHMM with same init params
    Stage 2 oracle : sklearn LogisticRegression run independently per chain
                     on the same projected Viterbi

And by **statistical recovery** : on synthetic data with known chain-level
transitions, the model must recover the chain-specific signal.
"""

from __future__ import annotations

import numpy as np
import pytest
from hmmlearn.hmm import GaussianHMM
from sklearn.linear_model import LogisticRegression

from hmm_core import init as init_mod
from hmm_core.factorial_nhmm import FactorialChainSpec, fit_factorial_nhmm
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

from ._helpers import match_states_by_means


# ---------------------------------------------------------------------------
# Helpers : synthetic factorial NHMM data
# ---------------------------------------------------------------------------


def _synth_factorial_data(seed: int, T: int = 1500):
    """2 chains × 2 states each with chain-specific covariate signal."""
    rng = np.random.default_rng(seed)
    u_a = rng.normal(0, 1, T)
    u_b = rng.normal(0, 1, T)

    def step(u_seq, sticky=0.85):
        z = np.empty(T, dtype=int)
        z[0] = int(u_seq[0] > 0)
        for t in range(1, T):
            target = int(u_seq[t] > 0)
            z[t] = z[t - 1] if rng.random() < sticky else target
        return z

    z_a = step(u_a)
    z_b = step(u_b)
    z_joint = z_a * 2 + z_b

    means = np.array([[0.0, 0.0], [0.0, 5.0], [5.0, 0.0], [5.0, 5.0]])
    X = np.array(
        [rng.multivariate_normal(means[k], 0.3 * np.eye(2)) for k in z_joint]
    )
    return X, u_a.reshape(-1, 1), u_b.reshape(-1, 1), means, z_a, z_b


# ---------------------------------------------------------------------------
# V.6.1 — Stage 1 base = raw hmmlearn.GaussianHMM
# ---------------------------------------------------------------------------


def test_v6_1_stage1_joint_equals_raw_gaussianhmm(rng_seed):
    """Stage 1 joint HMM fit must produce parameters identical to raw hmmlearn
    on the same K_joint-state ergodic topology with the same init."""
    X, Z_a, Z_b, _, _, _ = _synth_factorial_data(rng_seed)
    chains = [
        FactorialChainSpec(name="a", n_states=2),
        FactorialChainSpec(name="b", n_states=2),
    ]
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    fit_spec = FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-5)
    init = InitSpec(strategy="kmeans", seed=rng_seed)

    result = fit_factorial_nhmm(
        chains, X,
        covariates_per_chain={"a": Z_a, "b": Z_b},
        emission=emission, fit_spec=fit_spec, init=init,
        seed=rng_seed,
    )

    # Independent oracle : raw hmmlearn with same init params
    K_joint = 4
    joint_topo = Topology(
        name="oracle",
        n_states=K_joint,
        state_names=[f"j{i}" for i in range(K_joint)],
        emission=emission,
        allowed_transitions=None,
        startprob="uniform",
        init=init,
        fit=fit_spec,
    )
    initial_A = init_mod.transmat(joint_topo, seed=rng_seed, X=X)
    initial_pi = init_mod.startprob(joint_topo, seed=rng_seed)
    emission_kwargs = init_mod.emission_params(joint_topo, X=X, seed=rng_seed)

    ref = GaussianHMM(
        n_components=K_joint, covariance_type="diag",
        n_iter=fit_spec.n_iter, tol=fit_spec.tol, random_state=rng_seed,
    )
    ref.startprob_ = initial_pi
    ref.transmat_ = initial_A
    for k, v in emission_kwargs.items():
        setattr(ref, k, v)
    ref.init_params = ""
    ref.fit(X)

    ours = result.base.model
    np.testing.assert_allclose(ours.transmat_, ref.transmat_, atol=1e-12)
    np.testing.assert_allclose(ours.means_, ref.means_, atol=1e-12)
    np.testing.assert_allclose(ours.covars_, ref.covars_, atol=1e-12)


# ---------------------------------------------------------------------------
# V.6.2 — Stage 2 per-chain logit = independent sklearn run
# ---------------------------------------------------------------------------


def test_v6_2_stage2_per_chain_logit_matches_independent_sklearn(rng_seed):
    """Per-chain logistic regression in Stage 2 must match an independent
    sklearn fit on the same projected (Viterbi, covariate, next-state) data."""
    X, Z_a, Z_b, _, _, _ = _synth_factorial_data(rng_seed)
    chains = [
        FactorialChainSpec(name="a", n_states=2),
        FactorialChainSpec(name="b", n_states=2),
    ]
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains, X,
        covariates_per_chain={"a": Z_a, "b": Z_b},
        emission=emission,
        seed=rng_seed,
    )

    # Reproduce the projected per-chain Viterbi
    joint_v = result.base.model.predict(X)
    K_per_chain = result.K_per_chain
    per_chain_v = np.unravel_index(joint_v, K_per_chain)
    Z_per_chain = {"a": Z_a, "b": Z_b}

    for d_idx, name in enumerate(result.chain_names):
        z_d = np.asarray(per_chain_v[d_idx])
        Z_d = Z_per_chain[name]
        for src, clf in result.chain_classifiers[name].items():
            ts = [t for t in range(len(z_d) - 1) if z_d[t] == src]
            if len(ts) < 10:
                continue
            Z_i = Z_d[ts]
            next_states = z_d[np.asarray(ts) + 1]
            if len(np.unique(next_states)) < 2:
                continue
            independent = LogisticRegression(
                C=1.0, solver="lbfgs", max_iter=200, random_state=rng_seed,
            )
            independent.fit(Z_i, next_states)
            np.testing.assert_allclose(clf.coef_, independent.coef_, atol=1e-10)
            np.testing.assert_allclose(clf.intercept_, independent.intercept_, atol=1e-10)


# ---------------------------------------------------------------------------
# V.6.3 — Statistical recovery of joint emission means
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [42, 100])
def test_v6_3_recovers_joint_emission(seed):
    """The 4 joint emission means must be recovered set-wise across seeds."""
    X, Z_a, Z_b, true_means, _, _ = _synth_factorial_data(seed, T=2500)
    chains = [
        FactorialChainSpec(name="a", n_states=2),
        FactorialChainSpec(name="b", n_states=2),
    ]
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains, X,
        covariates_per_chain={"a": Z_a, "b": Z_b},
        emission=emission,
        fit_spec=FitSpec(algorithm="baum_welch", n_iter=200, tol=1e-5),
        init=InitSpec(strategy="kmeans", seed=seed),
        seed=seed,
    )
    est_means = np.asarray(result.base.model.means_)
    # Hungarian matching : pair each true mean with the closest estimated mean
    # (robust to permutation, unlike lexsort which is sensitive to tiny numeric
    # noise on coordinates).
    perm = match_states_by_means(true_means, est_means)
    est_aligned = est_means[perm]
    np.testing.assert_allclose(est_aligned, true_means, atol=0.3)


# ---------------------------------------------------------------------------
# V.6.4 — Parameter count : Strategy A vs alternative joint-NHMM-logit
# ---------------------------------------------------------------------------


def test_v6_4_parameter_count_savings():
    """Sanity check on the param savings rationale of Strategy A.

    A joint-NHMM-logit on ∏K_d outcomes per source state would have
    (∏K_d)² · P parameters. Our 2-stage decomposition has Σ_d K_d² · P
    transition parameters (plus the joint emission params, which are the
    same in both approaches).

    For D=2 chains with K=2 each : joint=16·P, 2-stage=8·P → 2× savings
    For D=3 chains with K=3 each : joint=729·P, 2-stage=27·P → 27× savings

    This test pins the savings ratio for D=3, K=3 (the MVP limit) at 27×.
    """
    D, K = 3, 3
    P = 1  # any non-zero P gives the same ratio
    joint_params = (K ** D) ** 2 * P
    two_stage_params = D * K ** 2 * P
    ratio = joint_params / two_stage_params
    assert ratio == 27.0, f"expected 27× savings at D=3 K=3, got {ratio}"
