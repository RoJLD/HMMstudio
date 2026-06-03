"""Smoke tests for the rSLDS backend (Phase D spike).

The registration test is opt-in: it requires ssm, which is a soft optional
dependency. The bundle adapter test uses hand-built fakes (SimpleNamespace) so
it runs everywhere — both inside the rslds Docker container AND on the bare
Windows host without ssm. This is the point of the dual-surface adapter: its
interface should be testable independently of the heavy backend.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest


def test_rslds_backend_registered():
    """When ssm is installed, the 'rslds' backend must appear in the registry."""
    pytest.importorskip("ssm")
    from hmm_core.backends import get_backend, list_backends

    assert "rslds" in list_backends()
    backend = get_backend("rslds")
    assert backend.name == "rslds"


def test_bundle_exposes_both_surfaces():
    """RSLDSFittedBundle must expose both rSLDS-native and hmmlearn-shaped attrs.

    Uses hand-built fakes (no ssm import) so this test runs everywhere. Verifies
    the interface contract of the bundle in isolation from the backend it wraps.
    """
    # Import direct from the module so we don't go through the lazy registry
    # path that may skip ssm; the bundle dataclass itself has no ssm dependency.
    from hmm_core.backends.rslds_backend import (
        RSLDSFittedBundle,
        _RSLDSMonitor,
    )

    K, D, N, T = 3, 2, 4, 20
    fake_model = SimpleNamespace(
        dynamics=SimpleNamespace(
            As=np.random.RandomState(0).randn(K, D, D),
            bs=np.random.RandomState(1).randn(K, D),
        ),
        emissions=SimpleNamespace(
            Cs=[np.random.RandomState(2).randn(N, D)],
            ds=[np.random.RandomState(3).randn(N)],
        ),
    )
    rng = np.random.RandomState(4)
    # discrete_expectations: list per sequence of (Ez (T, K), Ezzp1 (T-1, K, K), _)
    Ez = rng.dirichlet(np.ones(K), size=T)
    # NOTE: real ssm pairwise marginals satisfy Ezzp1[t].sum() == 1 (joint
    # over the pair (z_t, z_{t+1})), not per-row. Our fake is row-stochastic
    # — wrong as a faithful mock — but the bundle's transmat_ renormalizes
    # rows anyway, so only the (T-1, K, K) shape is load-bearing here. If
    # you extend this test to assert on stationary properties, replace with
    # a joint-marginal fake (e.g. Dirichlet on flattened K*K).
    Ezzp1 = rng.dirichlet(np.ones(K), size=(T - 1, K))
    fake_q = SimpleNamespace(
        mean_continuous_states=[rng.randn(T, D)],
        discrete_expectations=[(Ez, Ezzp1, None)],
    )
    elbo_history = [-100.0, -50.0, -49.5, -49.49, -49.489]

    bundle = RSLDSFittedBundle(
        model=fake_model,
        q_train=fake_q,
        D_latent=D,
        regularize="none",
        n_features=N,
        K=K,
        elbo_history=elbo_history,
    )

    # ---- rSLDS-native surface
    assert bundle.dynamics_As.shape == (K, D, D)
    assert bundle.dynamics_bs.shape == (K, D)
    assert bundle.emissions_Cs.shape == (N, D)
    assert bundle.emissions_ds.shape == (N,)
    assert bundle.latent_states.shape == (T, D)

    # ---- hmmlearn-shaped surface
    transmat = bundle.transmat_
    assert transmat.shape == (K, K)
    np.testing.assert_allclose(transmat.sum(axis=1), np.ones(K), atol=1e-9)

    startprob = bundle.startprob_
    assert startprob.shape == (K,)
    np.testing.assert_allclose(startprob.sum(), 1.0, atol=1e-9)

    monitor = bundle.monitor_
    assert isinstance(monitor, _RSLDSMonitor)
    assert monitor.history == elbo_history
    assert monitor.converged is True   # last two ELBOs differ by < 1e-3 relative

    # ---- convergence flag negative case
    bundle_diverged = RSLDSFittedBundle(
        model=fake_model, q_train=fake_q, D_latent=D, regularize="none",
        n_features=N, K=K, elbo_history=[-100.0, -50.0, -10.0],
    )
    assert bundle_diverged.monitor_.converged is False


@pytest.fixture
def toy_X():
    rng = np.random.default_rng(0)
    return rng.normal(size=(60, 4)).astype(np.float64)


@pytest.fixture
def toy_topology_k3():
    """Minimal Topology with K=3 Gaussian states — emission type chosen for
    schema validity only; rSLDS ignores emission_kwargs in the spike."""
    from hmm_core.topology import (
        EmissionSpec, FitSpec, InitSpec, Topology,
    )
    return Topology(
        name="rslds_smoke",
        n_states=3,
        state_names=["s0", "s1", "s2"],
        emission=EmissionSpec(type="gaussian", n_features=4, covariance_type="full"),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-4),
    )


def test_rslds_fit_rejects_one_feature(toy_topology_k3):
    """RSLDSBackend.fit must raise ValueError when n_features < 2.

    ssm.SLDS uses orthogonal emissions by default and requires N > D with
    D >= 1; passing a 1-feature matrix would otherwise crash deep in ssm
    initialization with a cryptic message. Runs on the host (validation
    fires before any ssm import)."""
    from hmm_core.backends.rslds_backend import RSLDSBackend

    backend = RSLDSBackend()
    X_one_feature = np.zeros((50, 1))
    K = toy_topology_k3.n_states
    with pytest.raises(ValueError, match="n_features"):
        backend.fit(
            toy_topology_k3, X_one_feature,
            seed=0, lengths=None,
            initial_transmat=np.full((K, K), 1.0 / K),
            initial_startprob=np.full(K, 1.0 / K),
            emission_kwargs={},
            mask=np.ones((K, K), dtype=bool),
        )


def test_rslds_smoke_fit(toy_X, toy_topology_k3):
    """End-to-end fit on tiny synthetic data inside the container."""
    pytest.importorskip("ssm")

    from hmm_core.backends import get_backend
    from hmm_core.backends._protocol import BackendFitResult
    from hmm_core.backends.rslds_backend import RSLDSFittedBundle

    backend = get_backend("rslds")
    K = toy_topology_k3.n_states
    N = toy_X.shape[1]
    result = backend.fit(
        toy_topology_k3, toy_X,
        seed=0, lengths=None,
        initial_transmat=np.full((K, K), 1.0 / K),
        initial_startprob=np.full(K, 1.0 / K),
        emission_kwargs={},
        mask=np.ones((K, K), dtype=bool),
    )

    assert isinstance(result, BackendFitResult)
    assert isinstance(result.model, RSLDSFittedBundle)
    assert result.transmat.shape == (K, K)
    np.testing.assert_allclose(result.transmat.sum(axis=1), 1.0, atol=1e-9)
    assert result.startprob.shape == (K,)
    assert np.isfinite(result.log_likelihood)
    assert result.n_iter_actual == toy_topology_k3.fit.n_iter
    # D_latent heuristic : max(1, min(K, N-1)) → with K=3, N=4 → 3
    assert result.model.D_latent == 3
    # Bundle exposes the dual surface
    assert hasattr(result.model, "dynamics_As")
    assert hasattr(result.model, "transmat_")
