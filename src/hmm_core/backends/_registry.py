"""Tiny registry to look up HMM backends by name.

Keeps a process-global mapping ``name -> backend factory``. A factory is
anything callable with no required arguments that returns an
:class:`HMMBackend`. The simplest factory is the backend class itself.
"""

from __future__ import annotations

from typing import Callable

from hmm_core.backends._protocol import HMMBackend

_REGISTRY: dict[str, Callable[[], HMMBackend]] = {}
_DEFAULT: list[str] = []  # single-element holder so we can mutate at import


def register_backend(
    name: str,
    factory: Callable[[], HMMBackend],
    *,
    default: bool = False,
) -> None:
    """Register a backend factory under ``name``.

    Set ``default=True`` to make this backend the one returned by
    :func:`get_backend` when called without an argument. Subsequent
    registrations with ``default=True`` override the previous default.
    """
    _REGISTRY[name] = factory
    if default or not _DEFAULT:
        _DEFAULT[:] = [name]


def get_backend(name: str | None = None) -> HMMBackend:
    """Return an instance of the requested backend (default if omitted)."""
    if name is None:
        if not _DEFAULT:
            raise RuntimeError("no default HMM backend registered")
        name = _DEFAULT[0]
    try:
        factory = _REGISTRY[name]
    except KeyError as exc:
        available = sorted(_REGISTRY)
        raise ValueError(f"unknown HMM backend: {name!r} (registered: {available})") from exc
    return factory()


def list_backends() -> list[str]:
    """Sorted list of registered backend names."""
    return sorted(_REGISTRY)
