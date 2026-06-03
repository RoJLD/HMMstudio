"""Backend abstraction for the HMM fit engine.

This package isolates the choice of underlying HMM library so the rest of
``hmm_core`` does not depend on ``hmmlearn`` (or any other engine) directly.

The contract is the :class:`HMMBackend` protocol below. Any conforming
implementation can be registered via :func:`register_backend` and selected
via :func:`get_backend`. Today only the ``hmmlearn`` backend is shipped;
candidates for the future include ``pomegranate``, ``dynamax`` (JAX, GPU),
and a pure-NumPy reference implementation.
"""

from __future__ import annotations

from hmm_core.backends._protocol import BackendFitResult, HMMBackend
from hmm_core.backends._registry import get_backend, list_backends, register_backend
from hmm_core.backends.hmmlearn_backend import HmmlearnBackend

# Self-register the default backend so callers can simply do
# ``get_backend("hmmlearn")`` or ``get_backend()`` for the default.
register_backend("hmmlearn", HmmlearnBackend, default=True)

# Bayesian backend (Phase A.6) is optional — pymc is a heavy soft dependency.
# Register it lazily so users who don't have pymc installed pay no import cost.
try:
    from hmm_core.backends.bayesian_backend import BayesianHMMBackend

    register_backend("bayesian", BayesianHMMBackend, default=False)
except ImportError:
    # pymc not installed — silently skip registration. The user gets a clear
    # error from get_backend("bayesian") if they try to use it without pymc.
    BayesianHMMBackend = None  # type: ignore[assignment]

# rSLDS backend (Phase D spike) is optional — ssm has Cython C-extensions that
# require a C compiler at install. Register lazily so users without ssm pay no
# import cost.
try:
    from hmm_core.backends.rslds_backend import RSLDSBackend

    register_backend("rslds", RSLDSBackend, default=False)
except ImportError:
    # ssm not installed — silently skip registration. get_backend("rslds") will
    # raise a clear "unknown HMM backend" error if the user tries to use it.
    RSLDSBackend = None  # type: ignore[assignment]

__all__ = [
    "BackendFitResult",
    "BayesianHMMBackend",
    "HMMBackend",
    "HmmlearnBackend",
    "RSLDSBackend",
    "get_backend",
    "list_backends",
    "register_backend",
]
