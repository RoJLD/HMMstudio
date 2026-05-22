"""Public fit() dispatcher and FittedModel container.

The heavy lifting (running EM, applying the transition mask at every M-step)
lives in ``hmm_core.backends``. This module is the orchestrator: it validates,
runs the init strategies, picks a backend, computes BIC/AIC, and packages
everything in a :class:`FittedModel`.
"""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass

import numpy as np

from hmm_core import init as init_mod
from hmm_core.backends import HMMBackend, get_backend
from hmm_core.topology import Topology


@dataclass(frozen=True)
class FittedModel:
    model: object
    topology: Topology
    log_likelihood: float
    bic: float
    aic: float
    n_iter_actual: int
    converged: bool
    seed: int
    duration_seconds: float


def _n_params(K: int, emission_spec) -> int:
    """Free parameters for BIC/AIC."""
    transitions = K * (K - 1) + (K - 1)
    e = emission_spec
    if e.type == "gaussian":
        D = e.n_features
        if e.covariance_type == "full":
            cov = K * D * (D + 1) // 2
        elif e.covariance_type == "diag":
            cov = K * D
        elif e.covariance_type == "tied":
            cov = D * (D + 1) // 2
        else:  # spherical
            cov = K
        return transitions + K * D + cov
    if e.type == "gmm":
        D, M = e.n_features, e.n_mix
        if e.covariance_type == "full":
            cov_total = K * M * D * (D + 1) // 2
        elif e.covariance_type == "diag":
            cov_total = K * M * D
        elif e.covariance_type == "tied":
            cov_total = K * D * (D + 1) // 2  # one matrix per state, shared across mixtures
        else:  # spherical
            cov_total = K * M
        return transitions + K * M * D + cov_total + K * (M - 1)
    if e.type == "multinomial":
        return transitions + K * (e.n_symbols - 1)
    if e.type == "poisson":
        return transitions + K * e.n_features
    raise ValueError(f"unsupported emission type for n_params: {e.type!r}")


def fit(
    topology: Topology,
    X: np.ndarray,
    *,
    seed: int | None = None,
    lengths: np.ndarray | None = None,
    backend: HMMBackend | str | None = None,
    states: np.ndarray | None = None,
    progress_callback=None,
) -> FittedModel:
    """Fit the HMM described by ``topology`` on observations ``X``.

    Parameters
    ----------
    topology : Topology
        Validated topology (validate() is called again defensively).
    X : ndarray
        Observations. Shape depends on emission type:
          - gaussian/gmm/poisson : (T, n_features)
          - multinomial          : (T, 1) integer values in [0, n_symbols)
    seed : int, optional
        Overrides ``topology.init.seed`` if provided.
    lengths : ndarray, optional
        Lengths of individual sequences in X (hmmlearn convention).  When
        provided, boundary transitions between sequences are excluded from the
        data_frequencies transition count and lengths is forwarded to
        ``model.fit``.
    backend : HMMBackend or str, optional
        Backend to use for the fit. Defaults to the registered default
        backend (``"hmmlearn"`` today). Pass a string (``"hmmlearn"``) to look
        up a registered backend by name, or an instance to use it directly.
    states : ndarray, optional
        Observed state labels (Phase A.7). When omitted (default), training is
        unsupervised via Baum-Welch EM. When provided as a fully-labeled
        integer array of shape ``(len(X),)`` with values in ``[0, n_states)``,
        training is **supervised**: closed-form MLE (count-based transitions
        and per-state emission statistics), one pass, deterministic. Partial
        labels (NaN positions) are reserved for semi-supervised training
        (Phase A.7.1, not yet implemented).
    progress_callback : callable, optional
        Called periodically during unsupervised (Baum-Welch) training with
        the current ``monitor_.history`` list.  Signature::

            progress_callback(history: list[float]) -> None

        Exceptions raised inside the callback are silently suppressed so they
        cannot interrupt the fit.  Not forwarded for supervised fits.
    """
    topology.validate()
    actual_seed = seed if seed is not None else topology.init.seed
    mask = topology.transition_mask()

    if isinstance(backend, str) or backend is None:
        backend_impl = get_backend(backend)
    else:
        backend_impl = backend

    if states is not None:
        states_arr = np.asarray(states)
        if states_arr.shape != (len(X),):
            raise ValueError(f"states must have shape ({len(X)},), got {states_arr.shape}")
        if states_arr.dtype.kind == "f" and np.isnan(states_arr).any():
            raise NotImplementedError(
                "semi-supervised mode (states with NaN entries) is planned "
                "for Phase A.7.1; for now provide a fully-labeled states "
                "array or omit it to run unsupervised Baum-Welch."
            )
        states_int = states_arr.astype(int)

        t0 = time.perf_counter()
        result = backend_impl.fit_supervised(
            topology,
            X,
            states_int,
            seed=actual_seed,
            lengths=lengths,
            mask=mask,
        )
        duration = time.perf_counter() - t0
    else:
        initial_A = init_mod.transmat(topology, seed=actual_seed, X=X, lengths=lengths)
        initial_pi = init_mod.startprob(topology, seed=actual_seed)
        emission_kwargs = init_mod.emission_params(topology, X=X, seed=actual_seed)

        transmat_prior = topology.transmat_prior()

        t0 = time.perf_counter()
        # Only pass optional kwargs to backends that declare the parameter,
        # so third-party backends implementing the original protocol still work.
        _backend_fit_params = inspect.signature(backend_impl.fit).parameters
        _extra = (
            {"progress_callback": progress_callback}
            if progress_callback is not None and "progress_callback" in _backend_fit_params
            else {}
        )
        if transmat_prior is not None and "transmat_prior" in _backend_fit_params:
            _extra["transmat_prior"] = transmat_prior
        result = backend_impl.fit(
            topology,
            X,
            seed=actual_seed,
            lengths=lengths,
            initial_transmat=initial_A,
            initial_startprob=initial_pi,
            emission_kwargs=emission_kwargs,
            mask=mask,
            **_extra,
        )
        duration = time.perf_counter() - t0

    n_params = _n_params(topology.n_states, topology.emission)
    n_obs = len(X)
    bic = float(-2.0 * result.log_likelihood + n_params * np.log(max(n_obs, 1)))
    aic = float(-2.0 * result.log_likelihood + 2.0 * n_params)

    return FittedModel(
        model=result.model,
        topology=topology,
        log_likelihood=result.log_likelihood,
        bic=bic,
        aic=aic,
        n_iter_actual=result.n_iter_actual,
        converged=result.converged,
        seed=actual_seed,
        duration_seconds=duration,
    )
