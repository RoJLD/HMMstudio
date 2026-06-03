"""Tests for Jupyter rich displays (Phase I.1).

Every major class must produce a well-formed HTML string from ``_repr_html_``
that contains the key information (state names, BIC, transmat values, etc.)
when displayed in Jupyter / IPython / VS Code notebooks / Colab.

We don't test rendering fidelity — we test that the method exists, returns
a string, contains expected anchors, and doesn't crash on edge cases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hmm_core.factorial_nhmm import FactorialChainSpec, fit_factorial_nhmm
from hmm_core.fit import fit
from hmm_core.gmm_nhmm import fit_gmm_nhmm
from hmm_core.nhmm import fit_nhmm
from hmm_core.prep import Pipeline
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_topology():
    return Topology(
        name="test_simple",
        n_states=3,
        state_names=["s0", "s1", "s2"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )


@pytest.fixture
def left_right_topology():
    return Topology(
        name="test_left_right",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )


@pytest.fixture
def gaussian_data():
    rng = np.random.default_rng(42)
    return np.concatenate(
        [
            rng.normal(0, 1, (60, 1)),
            rng.normal(5, 1, (60, 1)),
            rng.normal(-3, 1, (60, 1)),
        ]
    )


def _is_valid_html_snippet(s: str) -> bool:
    """Quick check that the string looks like reasonable HTML."""
    return (
        isinstance(s, str)
        and len(s) > 50
        and "<div" in s
        and "</div>" in s
        and ("<table" in s or "<h4" in s)
    )


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------


def test_topology_has_repr_html(simple_topology):
    assert hasattr(simple_topology, "_repr_html_")
    assert callable(simple_topology._repr_html_)


def test_topology_repr_html_returns_valid_html(simple_topology):
    html = simple_topology._repr_html_()
    assert _is_valid_html_snippet(html)


def test_topology_repr_html_contains_state_names(simple_topology):
    html = simple_topology._repr_html_()
    for name in simple_topology.state_names:
        assert name in html, f"state name {name!r} missing from HTML"


def test_topology_repr_html_contains_topology_name(simple_topology):
    html = simple_topology._repr_html_()
    assert simple_topology.name in html


def test_topology_repr_html_contains_emission_type(simple_topology):
    html = simple_topology._repr_html_()
    assert "gaussian" in html


def test_topology_repr_html_left_right_shows_forbidden_marker(left_right_topology):
    """Left-right topology must render forbidden cells with × marker."""
    html = left_right_topology._repr_html_()
    assert "×" in html, "forbidden cell marker missing in left-right HTML"


def test_topology_repr_html_contains_init_strategy(simple_topology):
    html = simple_topology._repr_html_()
    assert "kmeans" in html


# ---------------------------------------------------------------------------
# FittedModel
# ---------------------------------------------------------------------------


def test_fitted_model_repr_html(simple_topology, gaussian_data):
    result = fit(simple_topology, gaussian_data, seed=42)
    html = result._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "Log-likelihood" in html
    assert "BIC" in html
    # Should mention converged or iterations
    assert "converged" in html.lower() or "iter" in html.lower()


def test_fitted_model_repr_html_contains_state_names(simple_topology, gaussian_data):
    result = fit(simple_topology, gaussian_data, seed=42)
    html = result._repr_html_()
    for name in simple_topology.state_names:
        assert name in html


def test_fitted_model_left_right_shows_forbidden(left_right_topology, gaussian_data):
    result = fit(left_right_topology, gaussian_data, seed=42)
    html = result._repr_html_()
    assert "×" in html, "forbidden cells must be marked in fitted transmat heatmap"


# ---------------------------------------------------------------------------
# NHMMFittedModel
# ---------------------------------------------------------------------------


def test_nhmm_fitted_model_repr_html(simple_topology, gaussian_data):
    Z = np.random.default_rng(0).normal(0, 1, (len(gaussian_data), 2))
    result = fit_nhmm(simple_topology, gaussian_data, Z, covariate_names=["z0", "z1"], seed=42)
    html = result._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "NHMM" in html or "nhmm" in html.lower()
    assert "z0" in html and "z1" in html, "covariate names must appear"


# ---------------------------------------------------------------------------
# GMMNHMMFittedModel
# ---------------------------------------------------------------------------


def test_gmm_nhmm_fitted_model_repr_html():
    rng = np.random.default_rng(42)
    T = 300
    X = np.concatenate(
        [
            rng.normal([0, 0], 0.5, (T // 2, 2)),
            rng.normal([5, 5], 0.5, (T // 2, 2)),
        ]
    )
    Z = rng.normal(0, 1, (T, 1))

    topo = Topology(
        name="gmm_nhmm_repr",
        n_states=2,
        state_names=["a", "b"],
        emission=EmissionSpec(type="gmm", covariance_type="diag", n_features=2, n_mix=2),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )
    result = fit_gmm_nhmm(topo, X, Z, covariate_names=["z"], seed=42)
    html = result._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "GMM" in html
    assert "Sub-modes" in html or "sub-mode" in html.lower()


# ---------------------------------------------------------------------------
# FactorialNHMMFittedModel
# ---------------------------------------------------------------------------


def test_factorial_nhmm_fitted_model_repr_html():
    rng = np.random.default_rng(42)
    T = 300
    X = rng.normal(0, 1, (T, 2))
    chains = [
        FactorialChainSpec(name="trend", n_states=2),
        FactorialChainSpec(name="vol", n_states=2),
    ]
    result = fit_factorial_nhmm(
        chains,
        X,
        covariates_per_chain={"trend": rng.normal(0, 1, (T, 1)), "vol": rng.normal(0, 1, (T, 1))},
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
        seed=42,
    )
    html = result._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "Factorial" in html or "factorial" in html.lower()
    assert "trend" in html and "vol" in html
    assert "K_joint" in html


# ---------------------------------------------------------------------------
# Pipeline + PreparedResult
# ---------------------------------------------------------------------------


def test_pipeline_repr_html():
    pipe = Pipeline().add_step("log_diff", column="close", new_name="ret").add_step("dropna")
    html = pipe._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "log_diff" in html
    assert "dropna" in html
    assert "Pipeline" in html


def test_pipeline_recipe_repr_html():
    pipe = Pipeline.from_recipe("financial_log_returns")
    html = pipe._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "log_diff" in html  # from the financial_log_returns recipe


def test_prepared_result_repr_html():
    df = pd.DataFrame({"close": np.linspace(100, 110, 50), "volume": np.ones(50)})
    pipe = (
        Pipeline()
        .add_step("log_diff", column="close", new_name="ret")
        .add_step("dropna")
        .set_output(observations=["ret"], covariates=[])
    )
    result = pipe.fit_transform(df)
    html = result._repr_html_()
    assert _is_valid_html_snippet(html)
    assert "rows" in html
    assert "ret" in html


# ---------------------------------------------------------------------------
# Sanity : displayed HTML in IPython doesn't crash
# ---------------------------------------------------------------------------


def test_topology_displayed_via_ipython_protocol(simple_topology):
    """Calling _repr_html_ directly mimics what Jupyter / IPython does."""
    output = simple_topology._repr_html_()
    # IPython checks that the result is a string, not None, and not too small
    assert isinstance(output, str)
    assert len(output) > 100
