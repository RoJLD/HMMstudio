"""Smoke tests for the canonical Python snippets in README.md.

Why this file exists
--------------------
Before A.7 closed its user-facing surface, the README's "Supervised training"
section was calling a non-existent ``state_labels=`` kwarg. Anyone copying the
snippet would have hit ``TypeError: fit() got unexpected keyword argument``.
This file exists to make that class of drift a CI failure rather than a silent
documentation bug.

What we test
------------
We don't doctest the full README (some blocks need external data, others are
illustrative). Instead we execute the **canonical** snippets — the ones that
shape a newcomer's first 5 minutes — using fixture data shaped to match
each snippet's contract.

If you add or modify a Python snippet in README.md that introduces a new
public API surface, add a smoke test here too.
"""

from __future__ import annotations

import numpy as np

from hmm_core.fit import fit
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _well_separated_3state(states: np.ndarray, seed: int = 0) -> np.ndarray:
    """Trivially state-separable Gaussian observations (same recipe as
    tests/test_supervised.py::_well_separated_data)."""
    rng = np.random.default_rng(seed)
    centers = {k: 5.0 * float(k) for k in np.unique(states)}
    return np.array([rng.normal(centers[s], 0.3) for s in states]).reshape(-1, 1)


def _topo_3state() -> Topology:
    return Topology(
        name="readme_smoke_3state",
        n_states=3,
        state_names=["low", "mid", "high"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="uniform", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    )


# ---------------------------------------------------------------------------
# README "Quickstart in Jupyter" snippet — Topology + fit + predict
# ---------------------------------------------------------------------------


def test_readme_quickstart_snippet_runs():
    """The README quickstart claims: build topo, fit, decode. Verify it works."""
    topo = Topology(
        name="quickstart",
        n_states=3,
        state_names=["low", "mid", "high"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-4),
    )
    X = np.random.default_rng(42).normal(size=(200, 1))
    result = fit(topo, X, seed=42)

    viterbi_states = result.model.predict(X)
    assert viterbi_states.shape == (200,)
    assert viterbi_states.min() >= 0
    assert viterbi_states.max() < 3


# ---------------------------------------------------------------------------
# README "Supervised & semi-supervised training" snippet (Phase A.7)
# ---------------------------------------------------------------------------


def test_readme_supervised_snippet_signature():
    """README claims `result = fit(topo, X, states=y)` with `n_iter_actual == 1`.

    This is exactly the snippet that was BROKEN before A.7 user-facing close
    (used `state_labels=` instead of `states=`). Keep this assertion strict —
    if anyone renames the kwarg, this test fails immediately.
    """
    topo = _topo_3state()
    y = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 0, 1, 2, 0, 1, 2, 2, 2, 0, 1, 1])
    X = _well_separated_3state(y)

    # The README snippet, byte-for-byte (modulo variable names).
    result = fit(topo, X, states=y)

    assert result.n_iter_actual == 1, (
        "supervised closed-form MLE must be one-pass — if this fails, either "
        "the dispatcher regressed or the README snippet now lies."
    )


def test_readme_semi_supervised_snippet_runs():
    """README claims you can mark unlabelled positions with `np.nan` (float).

    The half-NaN array routes to constrained EM. We assert convergence,
    not exact iter count (semi-sup uses iterative EM, not closed-form).
    """
    topo = _topo_3state()
    y = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 0, 1, 2, 0, 1, 2, 2, 2, 0, 1, 1])
    X = _well_separated_3state(y)

    # README snippet: second half unobserved.
    y_partial = y.astype(float).copy()
    y_partial[len(y) // 2 :] = np.nan

    result = fit(topo, X, states=y_partial)
    # Just verify the fit completed (the topology is ergodic, K=3, so we
    # don't make claims about likelihood values — only that the dispatcher
    # accepted the call with the README signature).
    assert result.n_iter_actual >= 1
    assert np.isfinite(result.log_likelihood)


def test_readme_supervised_kwarg_name_is_stable():
    """Belt-and-braces: introspect `fit()`'s signature to confirm `states=` is
    a public keyword-only parameter. If this fails, it means the API was
    renamed and the README needs an update — fail loudly.
    """
    import inspect

    sig = inspect.signature(fit)
    assert "states" in sig.parameters, (
        "README documents fit(topo, X, states=...) — kwarg has vanished. "
        "Either restore it, or update README + this test."
    )
    # Ensure it's keyword-only so positional callers don't accidentally
    # bind the wrong arg.
    assert sig.parameters["states"].kind == inspect.Parameter.KEYWORD_ONLY
