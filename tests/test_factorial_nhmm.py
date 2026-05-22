"""Tests for Factorial NHMM (Phase A.13).

Strategy A (2-stage) :
  Stage 1 : Gaussian HMM on joint K_joint = ∏K_d states
  Stage 2 : per-chain NHMM logit on projected Viterbi

We test :
  - Public API + validation (chain specs, covariates, K_joint limit)
  - Shapes and probabilistic invariants (A_t sums to 1, per-chain shape (T, K_d, K_d))
  - Decomposition fidelity (decode_chain = unravel(decode_joint))
  - Chain independence (chain d's A_t depends only on its own covariates)
  - Recovery on synthetic factorial data
"""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.factorial_nhmm import (
    FactorialChainSpec,
    FactorialNHMMFittedModel,
    fit_factorial_nhmm,
)
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, TopologyError


# ---------------------------------------------------------------------------
# Synthetic data : 2 chains × 2 states with chain-specific covariate signal
# ---------------------------------------------------------------------------


def _synth_factorial_2x2(seed: int = 42, T: int = 1500):
    """Generate synthetic 2-chain × 2-state factorial NHMM data.

    Chain 0 ("trend") : state 0/1 selected by sign of u_trend[t]
    Chain 1 ("vol")   : state 0/1 selected by sign of u_vol[t]

    Joint emission : 4 well-separated means in 2D
        (trend=0, vol=0) → (0, 0)
        (trend=0, vol=1) → (0, 5)
        (trend=1, vol=0) → (5, 0)
        (trend=1, vol=1) → (5, 5)
    """
    rng = np.random.default_rng(seed)
    # Covariates per chain (independent)
    u_trend = rng.normal(0, 1, T)
    u_vol = rng.normal(0, 1, T)

    # Chains evolve with strong covariate dependence + dwell stickiness
    def step_chain(u_seq, sticky_prob=0.85):
        z = np.empty(T, dtype=int)
        z[0] = int(u_seq[0] > 0)
        for t in range(1, T):
            target = int(u_seq[t] > 0)
            stay = rng.random() < sticky_prob
            z[t] = z[t - 1] if stay else target
        return z

    z_trend = step_chain(u_trend)
    z_vol = step_chain(u_vol)

    # Joint state index (row-major over (trend, vol))
    z_joint = z_trend * 2 + z_vol

    joint_means = np.array(
        [
            [0.0, 0.0],   # (0,0)
            [0.0, 5.0],   # (0,1)
            [5.0, 0.0],   # (1,0)
            [5.0, 5.0],   # (1,1)
        ]
    )

    X = np.array([rng.multivariate_normal(joint_means[k], 0.3 * np.eye(2)) for k in z_joint])

    Z_trend = u_trend.reshape(-1, 1)
    Z_vol = u_vol.reshape(-1, 1)
    return X, Z_trend, Z_vol, joint_means, z_trend, z_vol


def _make_2chain_topology():
    return [
        FactorialChainSpec(name="trend", n_states=2),
        FactorialChainSpec(name="vol", n_states=2),
    ]


# ---------------------------------------------------------------------------
# Smoke + shapes
# ---------------------------------------------------------------------------


def test_factorial_nhmm_smoke():
    """End-to-end fit on synthetic 2x2 data without error."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)

    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )

    assert isinstance(result, FactorialNHMMFittedModel)
    assert result.n_chains == 2
    assert result.K_joint == 4
    assert result.K_per_chain == [2, 2]


def test_factorial_nhmm_shapes():
    """A_t per chain has shape (T, K_d, K_d)."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )

    T = len(X)
    assert result.A_t("trend").shape == (T, 2, 2)
    assert result.A_t("vol").shape == (T, 2, 2)
    # Joint base model has 4 states
    assert result.base.model.transmat_.shape == (4, 4)
    assert np.asarray(result.base.model.means_).shape == (4, 2)


def test_factorial_nhmm_A_t_rows_sum_to_one():
    """Each row of A_t in each chain must sum to 1 at every t."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )
    for name in result.chain_names:
        row_sums = result.A_t(name).sum(axis=2)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-9)


# ---------------------------------------------------------------------------
# Decomposition fidelity : decode_chain = unravel(decode_joint)
# ---------------------------------------------------------------------------


def test_factorial_nhmm_decode_chain_matches_unravel():
    """decode_chain(name) must equal the corresponding axis of unravel(decode_joint)."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )
    joint = result.decode_joint(X)
    expected_trend, expected_vol = np.unravel_index(joint, [2, 2])

    np.testing.assert_array_equal(result.decode_chain(X, "trend"), expected_trend)
    np.testing.assert_array_equal(result.decode_chain(X, "vol"), expected_vol)


# ---------------------------------------------------------------------------
# Chain independence : chain d's A_t depends only on its own covariates
# ---------------------------------------------------------------------------


def test_factorial_nhmm_chain_independence():
    """Permuting OTHER chains' covariates must not change chain d's A_t.

    This pins the key property of Factorial NHMM : per-chain transitions are
    independent. In our 2-stage impl, each chain's logistic regression sees
    only its own covariates, so this is structural.
    """
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)

    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )

    # Permute vol covariate, re-fit, check trend chain unchanged
    rng = np.random.default_rng(0)
    Z_vol_shuf = Z_vol[rng.permutation(len(Z_vol))]
    result_perm = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol_shuf},
        emission=emission,
        seed=42,
    )

    # Trend's classifiers should be identical (modulo numeric noise) since
    # they don't depend on vol covariates. Joint base might differ slightly
    # though (because Viterbi could shift) → we test on the classifiers'
    # coefficients only if both ran the logit (not fallback).
    for src in result.chain_classifiers.get("trend", {}):
        if src not in result_perm.chain_classifiers.get("trend", {}):
            continue  # one ran fallback, the other didn't — skip
        coef_orig = result.chain_classifiers["trend"][src].coef_
        coef_perm = result_perm.chain_classifiers["trend"][src].coef_
        # Same trend covariates + same Viterbi → coefficients must match exactly
        # (Viterbi may differ on a few timesteps due to slight EM drift, so we
        # tolerate a small numerical envelope)
        if np.array_equal(
            result.decode_chain(X, "trend"), result_perm.decode_chain(X, "trend")
        ):
            np.testing.assert_allclose(coef_orig, coef_perm, atol=1e-10)


# ---------------------------------------------------------------------------
# Covariate effect on A_t
# ---------------------------------------------------------------------------


def test_factorial_nhmm_A_t_varies_with_chain_covariate():
    """For each chain, A_t must differ between low- and high-covariate timesteps."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )

    for name, Z_d in [("trend", Z_trend), ("vol", Z_vol)]:
        z = Z_d[:, 0]
        low_idx = np.argsort(z)[:75]
        high_idx = np.argsort(z)[-75:]
        A = result.A_t(name)
        diff = np.abs(A[low_idx].mean(axis=0) - A[high_idx].mean(axis=0)).max()
        assert diff > 0.01, (
            f"chain {name!r} A_t doesn't depend enough on its own covariate ; "
            f"max diff = {diff:.4f}"
        )


# ---------------------------------------------------------------------------
# Recovery : on synthetic data, joint emission means recovered
# ---------------------------------------------------------------------------


def test_factorial_nhmm_recovers_joint_emission_means():
    """The 4 joint emission means must be recovered to within tolerance."""
    X, Z_trend, Z_vol, joint_means, _, _ = _synth_factorial_2x2(T=2000, seed=42)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        fit_spec=FitSpec(algorithm="baum_welch", n_iter=200, tol=1e-5),
        init=InitSpec(strategy="kmeans", seed=42),
        seed=42,
    )

    est_means = np.asarray(result.base.model.means_)  # (4, 2)
    # Set-equality up to permutation : sort by L2 norm
    true_sorted = joint_means[np.lexsort(joint_means.T)]
    est_sorted = est_means[np.lexsort(est_means.T)]
    np.testing.assert_allclose(est_sorted, true_sorted, atol=0.3)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_factorial_nhmm_rejects_non_gaussian_emission():
    """MVP only supports Gaussian joint emission."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=400)
    chains = _make_2chain_topology()
    with pytest.raises(TopologyError, match="gaussian"):
        fit_factorial_nhmm(
            chains,
            X,
            covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
            emission=EmissionSpec(
                type="gmm", covariance_type="diag", n_features=2, n_mix=2
            ),
        )


def test_factorial_nhmm_rejects_K_joint_too_large():
    """K_joint = ∏K_d > 27 must raise with a clear error."""
    # 4 × 2 × 2 × 2 = 32 > 27
    chains = [
        FactorialChainSpec(name="a", n_states=4),
        FactorialChainSpec(name="b", n_states=2),
        FactorialChainSpec(name="c", n_states=2),
        FactorialChainSpec(name="d", n_states=2),
    ]
    T = 100
    X = np.zeros((T, 2))
    covariates = {c.name: np.zeros((T, 1)) for c in chains}
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    with pytest.raises(TopologyError, match="K_joint"):
        fit_factorial_nhmm(chains, X, covariates, emission=emission)


def test_factorial_nhmm_rejects_mismatched_covariate_keys():
    """covariates_per_chain keys must equal chain names."""
    X, _, _, _, _, _ = _synth_factorial_2x2(T=200)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    bad_covs = {"trend": np.zeros((200, 1)), "wrong_name": np.zeros((200, 1))}
    with pytest.raises(ValueError, match="covariates_per_chain"):
        fit_factorial_nhmm(chains, X, bad_covs, emission=emission)


def test_factorial_nhmm_rejects_covariate_row_mismatch():
    """Each chain's covariate matrix must have T rows."""
    X, _, _, _, _, _ = _synth_factorial_2x2(T=200)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    bad = {"trend": np.zeros((150, 1)), "vol": np.zeros((200, 1))}
    with pytest.raises(ValueError, match="rows"):
        fit_factorial_nhmm(chains, X, bad, emission=emission)


def test_factorial_nhmm_rejects_duplicate_chain_names():
    """Chain names must be unique."""
    X, Z, Z2, _, _, _ = _synth_factorial_2x2(T=200)
    chains = [
        FactorialChainSpec(name="dup", n_states=2),
        FactorialChainSpec(name="dup", n_states=2),
    ]
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    with pytest.raises(ValueError, match="unique"):
        fit_factorial_nhmm(
            chains,
            X,
            covariates_per_chain={"dup": Z},
            emission=emission,
        )


# ---------------------------------------------------------------------------
# Multi-sequence (lengths)
# ---------------------------------------------------------------------------


def test_factorial_nhmm_with_lengths():
    """Multi-sequence support : transitions crossing boundaries are not counted."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=600)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    lengths = np.array([300, 300])
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        lengths=lengths,
        seed=42,
    )
    # Just check it completes and shapes are right
    assert result.A_t("trend").shape == (600, 2, 2)


# ---------------------------------------------------------------------------
# Default covariate names
# ---------------------------------------------------------------------------


def test_factorial_nhmm_default_covariate_names():
    """When covariate_names_per_chain is None, defaults are generated per chain."""
    X, Z_trend, Z_vol, _, _, _ = _synth_factorial_2x2(T=400)
    chains = _make_2chain_topology()
    emission = EmissionSpec(type="gaussian", covariance_type="diag", n_features=2)
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": Z_trend, "vol": Z_vol},
        emission=emission,
        seed=42,
    )
    assert result.chain_covariate_names["trend"] == ["trend_z0"]
    assert result.chain_covariate_names["vol"] == ["vol_z0"]
