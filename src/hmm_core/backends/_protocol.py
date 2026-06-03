"""Abstract contract for HMM fit backends.

A backend is the piece that actually runs Baum-Welch (or any equivalent
EM/MAP procedure), respects a binary transition mask, and produces a fitted
model object exposing the parameters and inference helpers we need.

Everything specific to a given library (``hmmlearn`` subclassing, JAX jit
boundaries, etc.) lives inside the concrete backend module — never in the
rest of ``hmm_core``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Protocol, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    from hmm_core.topology import Topology


@dataclass(frozen=True)
class BackendFitResult:
    """Backend-agnostic outcome of one fit() call.

    Attributes
    ----------
    model
        The fitted model object. Its concrete type is backend-specific (e.g.
        ``hmmlearn.hmm.GaussianHMM``). Consumers should only rely on the
        attributes documented below being present.
    transmat
        ``(K, K)`` transition matrix after the final M-step (mask applied).
    startprob
        ``(K,)`` initial-state distribution after fit.
    log_likelihood
        Log-likelihood ``model.score(X)`` of the training data under the fit.
    n_iter_actual
        Number of EM iterations actually run before convergence (or n_iter).
    converged
        True if the backend's convergence monitor reports convergence.
    convergence_history
        Per-iteration training log-likelihood trace from EM (empty for
        closed-form / supervised fits that run no EM loop).
    """

    model: Any
    transmat: np.ndarray
    startprob: np.ndarray
    log_likelihood: float
    n_iter_actual: int
    converged: bool
    convergence_history: tuple[float, ...] = ()


@runtime_checkable
class HMMBackend(Protocol):
    """Contract every fit backend must satisfy.

    Implementations are stateless: a single instance can serve many fits.
    Pre-computed quantities (initial transition matrix, initial startprob,
    initial emission parameters) are passed in — the backend is *not*
    responsible for the init strategies (those live in ``hmm_core.init``).
    """

    name: str

    def fit(
        self,
        topology: "Topology",
        X: np.ndarray,
        *,
        seed: int,
        lengths: np.ndarray | None,
        initial_transmat: np.ndarray,
        initial_startprob: np.ndarray,
        emission_kwargs: dict[str, np.ndarray],
        mask: np.ndarray,
        progress_callback: Callable[[list[float]], None] | None = None,
        transmat_prior: np.ndarray | None = None,
    ) -> BackendFitResult:
        """Run constrained Baum-Welch and return the fit result.

        Parameters
        ----------
        topology
            Validated topology describing the model.
        X
            Observations array, shape depends on emission type.
        seed
            Random seed for the underlying EM run.
        lengths
            Per-sequence lengths (hmmlearn convention) or None.
        initial_transmat
            Pre-computed initial transition matrix (K, K). Must already
            respect ``mask``.
        initial_startprob
            Pre-computed initial startprob (K,).
        emission_kwargs
            Pre-computed emission parameter overrides (means_, covars_, ...).
        mask
            Boolean (K, K) array. The backend must enforce ``transmat[i,j]==0``
            wherever ``mask[i,j]`` is False, at every M-step.
        progress_callback
            Optional callable invoked with the running log-likelihood history
            (``list[float]``) at sub-iteration intervals during the EM run.
            Backends that do not support live progress should ignore this
            argument. Used by the web UI (Phase B) to stream Baum-Welch
            convergence to clients via WebSocket.
        transmat_prior
            Optional (K, K) Dirichlet prior pseudo-count matrix. When provided,
            the backend should apply MAP smoothing in addition to mask
            enforcement during the M-step. None = no prior (MLE / current).

        Returns
        -------
        BackendFitResult
            See class docstring.
        """
        ...

    def fit_supervised(
        self,
        topology: "Topology",
        X: np.ndarray,
        states: np.ndarray,
        *,
        seed: int,
        lengths: np.ndarray | None,
        mask: np.ndarray,
    ) -> BackendFitResult:
        """Closed-form MLE fit when the latent state sequence is observed.

        No EM iteration: transitions are estimated by counting, emissions by
        per-state empirical statistics. Backends are free to delegate to a
        pure-numpy implementation since hmmlearn (and most engines) do not
        natively support supervised training.

        Parameters
        ----------
        states
            ``(T,)`` integer array of observed state labels. Values in
            ``[0, K)``. Must match the length of ``X`` (or of each sub-sequence
            implied by ``lengths``).
        mask
            Boolean ``(K, K)`` mask of allowed transitions. The backend MUST
            raise ``ValueError`` if ``states`` contains an observed transition
            on a forbidden edge.
        """
        ...

    def decode(self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None) -> np.ndarray:
        """Viterbi decode. Returns the most likely state sequence."""
        ...

    def predict_proba(
        self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None
    ) -> np.ndarray:
        """Forward-backward posteriors. Returns (T, K) array."""
        ...

    def score(self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None) -> float:
        """Log-likelihood of X under the fitted model."""
        ...
