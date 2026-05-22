"""Concrete ``HMMBackend`` implementation that wraps ``hmmlearn``.

This is the only module in ``hmm_core`` that imports from ``hmmlearn``
(transitively, via the ``Constrained*HMM`` subclasses in ``hmm_core.fit.*``).
Swap this file for ``pomegranate_backend.py`` etc. and the rest of the
package keeps working.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from hmm_core.backends._protocol import BackendFitResult
from hmm_core.fit._base import _apply_mask
from hmm_core.fit.gaussian import ConstrainedGaussianHMM
from hmm_core.fit.gmm import ConstrainedGMMHMM
from hmm_core.fit.multinomial import ConstrainedMultinomialHMM
from hmm_core.fit.poisson import ConstrainedPoissonHMM
from hmm_core.init import _empirical_covars
from hmm_core.topology import Topology

_CLASS_BY_EMISSION = {
    "gaussian": ConstrainedGaussianHMM,
    "gmm": ConstrainedGMMHMM,
    "multinomial": ConstrainedMultinomialHMM,
    "poisson": ConstrainedPoissonHMM,
}


def _hmmlearn_kwargs(topology: Topology, seed: int) -> dict:
    """Map EmissionSpec -> constructor kwargs for the hmmlearn class."""
    e = topology.emission
    common = {
        "n_components": topology.n_states,
        "n_iter": topology.fit.n_iter,
        "tol": topology.fit.tol,
        "random_state": seed,
    }
    if e.type in ("gaussian", "gmm"):
        common["covariance_type"] = e.covariance_type
    if e.type == "gmm":
        common["n_mix"] = e.n_mix
    if e.type == "multinomial":
        common["n_features"] = e.n_symbols
    return common


class HmmlearnBackend:
    """Backend that delegates to ``hmmlearn`` via the ``Constrained*HMM`` subclasses."""

    name = "hmmlearn"

    def fit(
        self,
        topology: Topology,
        X: np.ndarray,
        *,
        seed: int,
        lengths: np.ndarray | None,
        initial_transmat: np.ndarray,
        initial_startprob: np.ndarray,
        emission_kwargs: dict[str, np.ndarray],
        mask: np.ndarray,
    ) -> BackendFitResult:
        if topology.emission.type not in _CLASS_BY_EMISSION:
            raise ValueError(
                f"hmmlearn backend does not support emission: "
                f"{topology.emission.type!r} (supported: {sorted(_CLASS_BY_EMISSION)})"
            )

        cls = _CLASS_BY_EMISSION[topology.emission.type]
        kwargs = _hmmlearn_kwargs(topology, seed=seed)
        model = cls(transmat_mask=mask, **kwargs)

        model.startprob_ = initial_startprob
        model.transmat_ = initial_transmat
        skip_letters = "st"
        if emission_kwargs:
            for key, val in emission_kwargs.items():
                setattr(model, key, val)
            if "means_" in emission_kwargs:
                skip_letters += "m"
            if "covars_" in emission_kwargs:
                skip_letters += "c"
            if "weights_" in emission_kwargs:
                skip_letters += "w"
            if "emissionprob_" in emission_kwargs:
                skip_letters += "e"
            if "lambdas_" in emission_kwargs:
                skip_letters += "l"
        default_init = getattr(model, "init_params", "stmc")
        model.init_params = "".join(c for c in default_init if c not in skip_letters)

        if lengths is not None:
            model.fit(X, lengths=lengths)
        else:
            model.fit(X)

        log_lik = float(model.score(X))
        monitor = getattr(model, "monitor_", None)
        converged = bool(monitor.converged) if monitor is not None else False
        n_iter_actual = int(monitor.iter) if monitor is not None else topology.fit.n_iter

        return BackendFitResult(
            model=model,
            transmat=np.asarray(model.transmat_),
            startprob=np.asarray(model.startprob_),
            log_likelihood=log_lik,
            n_iter_actual=n_iter_actual,
            converged=converged,
        )

    def fit_supervised(
        self,
        topology: Topology,
        X: np.ndarray,
        states: np.ndarray,
        *,
        seed: int,
        lengths: np.ndarray | None,
        mask: np.ndarray,
    ) -> BackendFitResult:
        if topology.emission.type not in _CLASS_BY_EMISSION:
            raise ValueError(
                f"hmmlearn backend does not support emission: " f"{topology.emission.type!r}"
            )

        K = topology.n_states
        T = len(X)
        if states.shape != (T,):
            raise ValueError(f"states must have shape ({T},), got {states.shape}")
        if states.min() < 0 or states.max() >= K:
            raise ValueError(
                f"states values must be in [0, n_states={K}); "
                f"got min={int(states.min())} max={int(states.max())}"
            )
        states_i = states.astype(int)

        transmat = _supervised_transmat(states_i, K, mask, lengths)
        startprob = _supervised_startprob(states_i, K, lengths)
        emission_kwargs = _supervised_emission_mle(topology, X, states_i, K)

        cls = _CLASS_BY_EMISSION[topology.emission.type]
        kwargs = _hmmlearn_kwargs(topology, seed=seed)
        model = cls(transmat_mask=mask, **kwargs)
        model.startprob_ = startprob
        model.transmat_ = transmat
        for key, val in emission_kwargs.items():
            setattr(model, key, val)
        # No EM call — supervised is one closed-form pass. Mark every
        # parameter as "do not re-init from defaults" so any downstream
        # consumer that calls `.fit()` later won't wipe us out.
        model.init_params = ""

        log_lik = float(model.score(X, lengths=lengths))

        return BackendFitResult(
            model=model,
            transmat=transmat,
            startprob=startprob,
            log_likelihood=log_lik,
            n_iter_actual=1,
            converged=True,
        )

    def decode(self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None) -> np.ndarray:
        _, states = model.decode(X, lengths=lengths, algorithm="viterbi")
        return states

    def predict_proba(
        self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None
    ) -> np.ndarray:
        return model.predict_proba(X, lengths=lengths)

    def score(self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None) -> float:
        return float(model.score(X, lengths=lengths))


# ---------------------------------------------------------------------------
# Supervised MLE helpers (pure numpy — no hmmlearn dependency on this path)
# ---------------------------------------------------------------------------


def _iter_within_sequence(T: int, lengths: np.ndarray | None):
    """Yield (t, t+1) pairs that do NOT cross a sequence boundary."""
    if lengths is None:
        for t in range(T - 1):
            yield t, t + 1
        return
    offset = 0
    for L in lengths:
        for t in range(offset, offset + L - 1):
            yield t, t + 1
        offset += L


def _supervised_transmat(
    states: np.ndarray,
    K: int,
    mask: np.ndarray,
    lengths: np.ndarray | None,
) -> np.ndarray:
    counts = np.zeros((K, K))
    for t, t1 in _iter_within_sequence(len(states), lengths):
        counts[states[t], states[t1]] += 1

    forbidden = (counts > 0) & ~mask
    if forbidden.any():
        bad = np.argwhere(forbidden)
        examples = ", ".join(f"{i}->{j}" for i, j in bad[:5])
        raise ValueError(
            f"observed transitions violate topology mask "
            f"(forbidden edges observed: {examples}). "
            f"Either fix the labels or relax the topology's allowed_transitions."
        )

    # Smooth empty allowed rows so they don't sum to zero. We add a tiny
    # uniform pseudocount on allowed edges only; rows with real data are
    # essentially unaffected (1e-10 vs counts >= 1).
    counts = counts + 1e-10 * mask.astype(float)
    return _apply_mask(counts, mask)


def _supervised_startprob(
    states: np.ndarray,
    K: int,
    lengths: np.ndarray | None,
) -> np.ndarray:
    if lengths is None:
        first_states = [int(states[0])]
    else:
        first_states = []
        offset = 0
        for L in lengths:
            first_states.append(int(states[offset]))
            offset += L
    sp = np.bincount(first_states, minlength=K).astype(float)
    sp = sp + 1e-10  # avoid exact zeros
    sp /= sp.sum()
    return sp


def _supervised_emission_mle(
    topology: Topology,
    X: np.ndarray,
    states: np.ndarray,
    K: int,
) -> dict:
    """Closed-form MLE of emission parameters given observed state labels."""
    e = topology.emission

    if e.type == "gaussian":
        D = e.n_features
        X2 = X.reshape(-1, D)
        means = np.zeros((K, D))
        for k in range(K):
            pts = X2[states == k]
            if len(pts) > 0:
                means[k] = pts.mean(axis=0)
        covars = _empirical_covars(X2, states, K, e.covariance_type)
        return {"means_": means, "covars_": covars}

    if e.type == "multinomial":
        n_symbols = e.n_symbols
        emissionprob = np.zeros((K, n_symbols))
        X_int = X.astype(int).ravel()
        for k in range(K):
            X_k = X_int[states == k]
            counts_k = np.bincount(X_k, minlength=n_symbols).astype(float)
            total = counts_k.sum()
            if total > 0:
                emissionprob[k] = counts_k / total
            else:
                emissionprob[k] = 1.0 / n_symbols
        # Add tiny Laplace smoothing then renormalize so no symbol has
        # exact zero probability (would crash log-likelihood scoring).
        emissionprob = emissionprob + 1e-6
        emissionprob /= emissionprob.sum(axis=1, keepdims=True)
        return {"emissionprob_": emissionprob}

    if e.type == "poisson":
        D = e.n_features
        X2 = X.reshape(-1, D).astype(float)
        lambdas = np.zeros((K, D))
        for k in range(K):
            pts = X2[states == k]
            if len(pts) > 0:
                lambdas[k] = pts.mean(axis=0)
        return {"lambdas_": np.clip(lambdas, 1e-6, None)}

    if e.type == "gmm":
        # Supervised GMM means fitting M sub-components per state — that's
        # itself a small unsupervised problem. Punted to A.7.1.
        raise NotImplementedError(
            "supervised GMM training is not implemented yet; planned for A.7.1. "
            "Use type='gaussian' with covariance_type='full' as a workaround, "
            "or fall back to unsupervised fit() without states."
        )

    raise ValueError(f"unknown emission type for supervised MLE: {e.type!r}")
