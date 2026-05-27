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
    hqic: float
    n_obs: int
    n_iter_actual: int
    converged: bool
    seed: int
    duration_seconds: float

    def to_summary_dict(self) -> dict:
        """Return all regression-test / changelog relevant fit metadata as a flat dict.

        Useful for:

          - capturing reference values in regression tests
          - serialising fit results for run logs / CI dashboards
          - quickly inspecting a fit from a notebook

        Notes
        -----
        ``n_params`` is derived from the topology (BIC/AIC/HQIC convention used
        by the dispatcher). ``n_obs`` is the training-sequence length captured
        at fit time (needed for BIC and HQIC ; HQIC = -2·LL + 2·k·ln(ln(n))).
        """
        e = self.topology.emission
        return {
            "topology_name": self.topology.name,
            "n_states": int(self.topology.n_states),
            "emission_type": e.type,
            "n_features": e.n_features,
            "n_mix": e.n_mix,  # None for non-GMM
            "covariance_type": e.covariance_type,  # None for non-gaussian/gmm
            "log_likelihood": float(self.log_likelihood),
            "bic": float(self.bic),
            "aic": float(self.aic),
            "hqic": float(self.hqic),
            "n_obs": int(self.n_obs),
            "n_iter_actual": int(self.n_iter_actual),
            "converged": bool(self.converged),
            "n_params": int(_n_params(self.topology.n_states, e)),
            "seed": int(self.seed) if self.seed is not None else None,
            "duration_seconds": float(self.duration_seconds),
        }

    def to_summary_json(self, *, indent: int = 2) -> str:
        """JSON wrapper around :meth:`to_summary_dict`."""
        import json

        return json.dumps(self.to_summary_dict(), indent=indent, default=str)

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter (Phase I.1)."""
        from hmm_core._jupyter import (
            render_matrix_heatmap,
            render_stats_table,
            wrap_html,
        )

        # Top-line stats
        converged_html = (
            '<span class="ok">✓ converged</span>'
            if self.converged
            else '<span class="warn">✗ did not converge (hit n_iter)</span>'
        )
        stats_rows = [
            ("Topology", self.topology.name),
            ("States (K)", self.topology.n_states),
            ("Log-likelihood", f"{self.log_likelihood:.3f}"),
            ("BIC", f"{self.bic:.3f}"),
            ("AIC", f"{self.aic:.3f}"),
            ("HQIC", f"{self.hqic:.3f}"),
            ("Converged", converged_html),
            ("Iterations", f"{self.n_iter_actual} / {self.topology.fit.n_iter}"),
            ("Seed", self.seed),
            ("Duration", f"{self.duration_seconds:.2f}s"),
        ]
        stats_html = render_stats_table(stats_rows)

        # Heatmap of transmat (with forbidden mask)
        mask = self.topology.transition_mask()
        transmat = np.asarray(self.model.transmat_)
        heatmap_html = render_matrix_heatmap(
            transmat,
            self.topology.state_names,
            self.topology.state_names,
            forbidden_mask=mask,
            title="Fitted transmat (rows = from, cols = to)",
        )

        # Optional Viterbi strip on the original data — only if available cheaply.
        # We don't auto-decode here (no X stored on the FittedModel) ; users get
        # the strip when they call .predict() themselves.

        parts = [
            "<h4>FittedModel</h4>",
            stats_html,
            heatmap_html,
        ]
        return wrap_html(*parts)


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
        Observed state labels of shape ``(len(X),)``.

        - **Omitted (default)** → unsupervised Baum-Welch EM (Phase A).
        - **Fully labelled** integer array, all values in ``[0, n_states)``
          → **supervised** closed-form MLE (Phase A.7): count-based
          transitions, per-state emission statistics, one pass, deterministic.
        - **Partially labelled** → **semi-supervised** EM (Phase A.7.1).
          Mark unlabelled positions with ``NaN`` in a float array or with
          the sentinel ``-1`` in an int array. The backend runs a
          constrained Baum-Welch where the E-step is clamped to the known
          labels at labelled positions and free elsewhere. Initial
          parameters come from the supervised MLE on the labelled subset.
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

        # Detect semi-supervised vs fully-supervised. NaN entries (float) or
        # -1 sentinels (int / float) flag unlabelled positions and route to
        # the backend's semi-supervised EM (Phase A.7.1). Fully-int arrays
        # with all values in [0, K) take the closed-form supervised path.
        if states_arr.dtype.kind == "f":
            # Pass the float array through as-is — the backend treats NaN as
            # unlabelled. Out-of-range values are validated downstream.
            states_to_pass: np.ndarray = states_arr
        else:
            # Integer-ish array. -1 is the sentinel; other values must be in
            # [0, K). We let the backend handle range validation so the
            # error message lives in one place.
            states_to_pass = states_arr

        t0 = time.perf_counter()
        result = backend_impl.fit_supervised(
            topology,
            X,
            states_to_pass,
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
    # Hannan-Quinn : -2·LL + 2·k·ln(ln(n)). Penalty grows slower than BIC
    # (ln ln n vs ln n) but faster than AIC ; favoured for model-order
    # selection on long sequences where BIC over-penalises. ln(ln(n))
    # needs n ≥ 3 to stay positive ; clamp below that.
    hqic = float(-2.0 * result.log_likelihood + 2.0 * n_params * np.log(np.log(max(n_obs, 3))))

    return FittedModel(
        model=result.model,
        topology=topology,
        log_likelihood=result.log_likelihood,
        bic=bic,
        aic=aic,
        hqic=hqic,
        n_obs=n_obs,
        n_iter_actual=result.n_iter_actual,
        converged=result.converged,
        seed=actual_seed,
        duration_seconds=duration,
    )
