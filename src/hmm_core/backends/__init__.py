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

__all__ = [
    "BackendFitResult",
    "HMMBackend",
    "HmmlearnBackend",
    "get_backend",
    "list_backends",
    "register_backend",
]
