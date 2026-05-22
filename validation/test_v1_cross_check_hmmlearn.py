"""V.1 — Cross-check our fit() dispatcher against raw hmmlearn.

On ergodic topology without structural mask, our pipeline delegates fully
to hmmlearn. Final parameters must agree to 1e-12 ; any larger difference
indicates a wiring bug in our glue code, not a math issue.

The contract :
    1. Use our init module to compute initial (transmat, startprob, emission)
    2. Run our fit() → final params
    3. Run raw hmmlearn with the **same** initial params + init_params=""
    4. Assert all final params + log-likelihood agree to TOLERANCE

These tests are the safety net for every future change to the fit pipeline.
"""

from __future__ import annotations

import numpy as np
import pytest
from hmmlearn.hmm import CategoricalHMM, GaussianHMM, GMMHMM, PoissonHMM

from hmm_core import init as init_mod
from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

# Tolerance for "byte-identical to hmmlearn". We're not validating EM ;
# we're validating that our glue code does not perturb hmmlearn's output.
TOLERANCE = 1e-12


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_topology(emission_spec: EmissionSpec, K: int, init_strategy: str, seed: int) -> Topology:
    """Build an ergodic topology (no allowed_transitions = no mask)."""
    return Topology(
        name=f"v1-{emission_spec.type}",
        n_states=K,
        state_names=[f"s{i}" for i in range(K)],
        emission=emission_spec,
        allowed_transitions=None,  # ergodic
        startprob="uniform",
        init=InitSpec(strategy=init_strategy, seed=seed),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-6),
    )


def _build_reference_model(
    cls,
    K: int,
    n_iter: int,
    tol: float,
    seed: int,
    initial_pi: np.ndarray,
    initial_A: np.ndarray,
    emission_kwargs: dict,
    extra_kwargs: dict | None = None,
):
    """Build a raw hmmlearn model with our init params pre-set + auto-init disabled."""
    common = {
        "n_components": K,
        "n_iter": n_iter,
        "tol": tol,
        "random_state": seed,
    }
    if extra_kwargs:
        common.update(extra_kwargs)
    model = cls(**common)
    model.startprob_ = initial_pi
    model.transmat_ = initial_A
    for key, val in emission_kwargs.items():
        setattr(model, key, val)
    model.init_params = ""  # disable hmmlearn's auto-init for every param family
    return model


def _make_gaussian_data(seed: int, n_per_cluster: int = 50) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.concatenate(
        [
            rng.normal(0.0, 1.0, (n_per_cluster, 2)),
            rng.normal(5.0, 1.5, (n_per_cluster, 2)),
            rng.normal(-3.0, 0.5, (n_per_cluster, 2)),
        ]
    )


def _make_multinomial_data(seed: int, T: int = 200, n_symbols: int = 4) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_symbols, size=(T, 1))


def _make_poisson_data(seed: int, T: int = 200) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.concatenate(
        [
            rng.poisson(2.0, (T // 2, 1)),
            rng.poisson(10.0, (T // 2, 1)),
        ]
    ).astype(float)


def _assert_models_equal(ours, theirs, X, emission_attrs: list[str], tol: float = TOLERANCE):
    """Compare all relevant parameter arrays + log-likelihood.

    Tolerance separation :
      - **Parameter arrays** : compared to ``tol`` (default 1e-12). These are
        stored values produced by identical EM iterations on identical
        initial conditions ; they should be byte-identical modulo
        accumulated FP noise in M-step normalizations (negligible).
      - **Log-likelihood** : compared with ``rtol=tol`` (relative, not
        absolute). ``model.score(X)`` involves summing log-probs over T
        observations and (for GMM) over M mixture components, where
        BLAS-driven reordering of partial sums can introduce O(1e-12)
        relative differences even when parameters are identical. We accept
        relative match instead.
    """
    np.testing.assert_allclose(
        ours.transmat_, theirs.transmat_, atol=tol, err_msg="transmat divergent"
    )
    np.testing.assert_allclose(
        ours.startprob_, theirs.startprob_, atol=tol, err_msg="startprob divergent"
    )
    for attr in emission_attrs:
        np.testing.assert_allclose(
            getattr(ours, attr),
            getattr(theirs, attr),
            atol=tol,
            err_msg=f"{attr} divergent",
        )
    our_lp = float(ours.score(X))
    their_lp = float(theirs.score(X))
    assert our_lp == pytest.approx(their_lp, rel=tol), (
        f"log-likelihood divergent : ours={our_lp}, theirs={their_lp}, "
        f"diff={abs(our_lp - their_lp):.2e}"
    )


# ---------------------------------------------------------------------------
# V.1.1 — Gaussian ergodic
# ---------------------------------------------------------------------------


def test_v1_1_gaussian_ergodic_matches_hmmlearn(rng_seed):
    """Our fit() on ergodic Gaussian topology = raw hmmlearn.GaussianHMM."""
    K = 3
    X = _make_gaussian_data(rng_seed)
    topo = _build_topology(
        EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
        K=K,
        init_strategy="uniform",
        seed=rng_seed,
    )

    # Compute initial params via our init module (the reference must use these too)
    initial_A = init_mod.transmat(topo, seed=rng_seed, X=X)
    initial_pi = init_mod.startprob(topo, seed=rng_seed)
    emission_kwargs = init_mod.emission_params(topo, X=X, seed=rng_seed)

    # Our pipeline
    our_result = fit(topo, X, seed=rng_seed)

    # Reference : raw hmmlearn with same initial params
    ref = _build_reference_model(
        GaussianHMM,
        K=K,
        n_iter=topo.fit.n_iter,
        tol=topo.fit.tol,
        seed=rng_seed,
        initial_pi=initial_pi,
        initial_A=initial_A,
        emission_kwargs=emission_kwargs,
        extra_kwargs={"covariance_type": "diag"},
    )
    ref.fit(X)

    _assert_models_equal(our_result.model, ref, X, emission_attrs=["means_", "covars_"])


# ---------------------------------------------------------------------------
# V.1.2 — GMM ergodic
# ---------------------------------------------------------------------------


def test_v1_2_gmm_ergodic_matches_hmmlearn(rng_seed):
    """Our fit() on ergodic GMM topology = raw hmmlearn.GMMHMM."""
    K = 2
    M = 2
    X = _make_gaussian_data(rng_seed, n_per_cluster=75)
    topo = _build_topology(
        EmissionSpec(type="gmm", covariance_type="diag", n_features=2, n_mix=M),
        K=K,
        init_strategy="random",  # more error-prone, better stress test
        seed=rng_seed,
    )

    initial_A = init_mod.transmat(topo, seed=rng_seed, X=X)
    initial_pi = init_mod.startprob(topo, seed=rng_seed)
    emission_kwargs = init_mod.emission_params(topo, X=X, seed=rng_seed)

    our_result = fit(topo, X, seed=rng_seed)

    ref = _build_reference_model(
        GMMHMM,
        K=K,
        n_iter=topo.fit.n_iter,
        tol=topo.fit.tol,
        seed=rng_seed,
        initial_pi=initial_pi,
        initial_A=initial_A,
        emission_kwargs=emission_kwargs,
        extra_kwargs={"covariance_type": "diag", "n_mix": M},
    )
    ref.fit(X)

    _assert_models_equal(
        our_result.model, ref, X, emission_attrs=["means_", "covars_", "weights_"]
    )


# ---------------------------------------------------------------------------
# V.1.3 — Multinomial ergodic
# ---------------------------------------------------------------------------


def test_v1_3_multinomial_ergodic_matches_hmmlearn(rng_seed):
    """Our fit() on ergodic Multinomial topology = raw hmmlearn.CategoricalHMM."""
    K = 2
    n_symbols = 4
    X = _make_multinomial_data(rng_seed, T=300, n_symbols=n_symbols)
    topo = _build_topology(
        EmissionSpec(type="multinomial", n_symbols=n_symbols),
        K=K,
        init_strategy="uniform",
        seed=rng_seed,
    )

    initial_A = init_mod.transmat(topo, seed=rng_seed, X=X)
    initial_pi = init_mod.startprob(topo, seed=rng_seed)
    emission_kwargs = init_mod.emission_params(topo, X=X, seed=rng_seed)

    our_result = fit(topo, X, seed=rng_seed)

    ref = _build_reference_model(
        CategoricalHMM,
        K=K,
        n_iter=topo.fit.n_iter,
        tol=topo.fit.tol,
        seed=rng_seed,
        initial_pi=initial_pi,
        initial_A=initial_A,
        emission_kwargs=emission_kwargs,
        extra_kwargs={"n_features": n_symbols},
    )
    ref.fit(X)

    _assert_models_equal(our_result.model, ref, X, emission_attrs=["emissionprob_"])


# ---------------------------------------------------------------------------
# V.1.4 — Poisson ergodic
# ---------------------------------------------------------------------------


def test_v1_4_poisson_ergodic_matches_hmmlearn(rng_seed):
    """Our fit() on ergodic Poisson topology = raw hmmlearn.PoissonHMM."""
    K = 2
    X = _make_poisson_data(rng_seed, T=300)
    topo = _build_topology(
        EmissionSpec(type="poisson", n_features=1),
        K=K,
        init_strategy="uniform",
        seed=rng_seed,
    )

    initial_A = init_mod.transmat(topo, seed=rng_seed, X=X)
    initial_pi = init_mod.startprob(topo, seed=rng_seed)
    emission_kwargs = init_mod.emission_params(topo, X=X, seed=rng_seed)

    our_result = fit(topo, X, seed=rng_seed)

    ref = _build_reference_model(
        PoissonHMM,
        K=K,
        n_iter=topo.fit.n_iter,
        tol=topo.fit.tol,
        seed=rng_seed,
        initial_pi=initial_pi,
        initial_A=initial_A,
        emission_kwargs=emission_kwargs,
    )
    ref.fit(X)

    _assert_models_equal(our_result.model, ref, X, emission_attrs=["lambdas_"])
