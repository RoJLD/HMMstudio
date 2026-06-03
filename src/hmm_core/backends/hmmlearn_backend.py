"""Concrete ``HMMBackend`` implementation that wraps ``hmmlearn``.

This is the only module in ``hmm_core`` that imports from ``hmmlearn``
(transitively, via the ``Constrained*HMM`` subclasses in ``hmm_core.fit.*``).
Swap this file for ``pomegranate_backend.py`` etc. and the rest of the
package keeps working.
"""

from __future__ import annotations

import threading
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
        progress_callback=None,
        transmat_prior: np.ndarray | None = None,
    ) -> BackendFitResult:
        if topology.emission.type not in _CLASS_BY_EMISSION:
            raise ValueError(
                f"hmmlearn backend does not support emission: "
                f"{topology.emission.type!r} (supported: {sorted(_CLASS_BY_EMISSION)})"
            )

        cls = _CLASS_BY_EMISSION[topology.emission.type]
        kwargs = _hmmlearn_kwargs(topology, seed=seed)
        model = cls(transmat_mask=mask, transmat_prior=transmat_prior, **kwargs)

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

        # Fix #7: translate FitSpec.freeze_startprob / freeze_transmat into
        # hmmlearn's per-EM-step `params` string. Removing a letter prevents
        # the corresponding M-step from updating that parameter. Emission
        # letters (m / c / w / e / l) are always kept so EM still fits them.
        if topology.fit.freeze_startprob or topology.fit.freeze_transmat:
            default_params = getattr(model, "params", default_init)
            params_letters = list(default_params)
            if topology.fit.freeze_startprob and "s" in params_letters:
                params_letters.remove("s")
            if topology.fit.freeze_transmat and "t" in params_letters:
                params_letters.remove("t")
            model.params = "".join(params_letters)

        # Spawn a polling thread when a progress_callback is provided.
        # The thread reads model.monitor_.history every 200 ms while the
        # blocking model.fit() runs in this thread.
        stop_polling = None
        poll_thread = None
        if progress_callback is not None:
            stop_polling = threading.Event()

            def _poll():
                while not stop_polling.is_set():
                    monitor = getattr(model, "monitor_", None)
                    history = list(getattr(monitor, "history", [])) if monitor is not None else []
                    if history:
                        try:
                            progress_callback(history)
                        except Exception:
                            pass  # callback failures must not break the fit
                    stop_polling.wait(0.2)

            poll_thread = threading.Thread(target=_poll, daemon=True)
            poll_thread.start()

        try:
            if lengths is not None:
                model.fit(X, lengths=lengths)
            else:
                model.fit(X)
        finally:
            if stop_polling is not None:
                stop_polling.set()
                poll_thread.join(timeout=1.0)
                # Final callback with the complete history so callers always
                # receive at least one invocation even for very fast fits.
                monitor = getattr(model, "monitor_", None)
                history = list(getattr(monitor, "history", [])) if monitor is not None else []
                if history:
                    try:
                        progress_callback(history)
                    except Exception:
                        pass

        log_lik = float(model.score(X))
        monitor = getattr(model, "monitor_", None)
        converged = bool(monitor.converged) if monitor is not None else False
        n_iter_actual = int(monitor.iter) if monitor is not None else topology.fit.n_iter

        history = tuple(float(x) for x in getattr(monitor, "history", []) or [])
        return BackendFitResult(
            model=model,
            transmat=np.asarray(model.transmat_),
            startprob=np.asarray(model.startprob_),
            log_likelihood=log_lik,
            n_iter_actual=n_iter_actual,
            converged=converged,
            convergence_history=history,
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
        states_arr = np.asarray(states)
        if states_arr.shape != (T,):
            raise ValueError(f"states must have shape ({T},), got {states_arr.shape}")

        # Detect semi-supervised mode (A.7.1): NaN entries (float arrays) or
        # -1 sentinels (int arrays) flag unlabelled positions.
        is_unlabelled = np.zeros(T, dtype=bool)
        if states_arr.dtype.kind == "f":
            is_unlabelled |= np.isnan(states_arr)
        if states_arr.dtype.kind in ("i", "u", "f"):
            with np.errstate(invalid="ignore"):
                is_unlabelled |= states_arr == -1
        if is_unlabelled.all():
            raise ValueError(
                "fit_supervised called with no labelled positions; use the "
                "unsupervised fit() (states=None) instead."
            )
        if is_unlabelled.any():
            return self._fit_semi_supervised(
                topology,
                X,
                states_arr,
                is_unlabelled,
                seed=seed,
                lengths=lengths,
                mask=mask,
            )

        # Fully-supervised path: cast safely now that we know no NaN / -1.
        labelled_int = states_arr.astype(int)
        if labelled_int.min() < 0 or labelled_int.max() >= K:
            raise ValueError(
                f"states values must be in [0, n_states={K}); "
                f"got min={int(labelled_int.min())} max={int(labelled_int.max())}"
            )

        transmat = _supervised_transmat(labelled_int, K, mask, lengths)
        startprob = _supervised_startprob(labelled_int, K, lengths)
        emission_kwargs = _supervised_emission_mle(topology, X, labelled_int, K)

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

    def _fit_semi_supervised(
        self,
        topology: Topology,
        X: np.ndarray,
        states: np.ndarray,
        is_unlabelled: np.ndarray,
        *,
        seed: int,
        lengths: np.ndarray | None,
        mask: np.ndarray,
    ) -> BackendFitResult:
        """Constrained EM with E-step clamped at labelled positions.

        Initial parameters come from the fully-supervised MLE on the labelled
        subset. The EM loop is hmmlearn's standard machinery; we hook the
        label-clamp by setting ``model._label_clamp`` so each
        ``Constrained*HMM._compute_log_likelihood`` injects -inf at the
        forbidden states for labelled positions. After EM converges we clear
        the clamp so ``.score()`` returns an unconstrained log-likelihood.
        """
        K = topology.n_states
        T = len(states)

        label_clamp = np.full(T, -1, dtype=int)
        labelled_mask = ~is_unlabelled
        labelled_vals = states[labelled_mask]
        # All labelled values must be valid in [0, K). NaN entries are
        # already filtered out by labelled_mask.
        labelled_int = labelled_vals.astype(int)
        if len(labelled_int) and (labelled_int.min() < 0 or labelled_int.max() >= K):
            raise ValueError(
                f"labelled states must be in [0, n_states={K}); "
                f"got min={int(labelled_int.min())} max={int(labelled_int.max())}"
            )
        label_clamp[labelled_mask] = labelled_int

        # 1. Validate any observed (labelled, labelled) adjacent transitions
        # honour the topology mask. Transitions crossing an unlabelled
        # position are left to EM to discover.
        _validate_labelled_transitions(label_clamp, mask, lengths)

        # 2. Initial parameters from supervised MLE on the labelled subset.
        labelled_idx = np.where(labelled_mask)[0]
        emission_kwargs = _supervised_emission_mle(topology, X[labelled_idx], labelled_int, K)
        initial_transmat = _semi_supervised_initial_transmat(label_clamp, K, mask, lengths)
        initial_startprob = _semi_supervised_initial_startprob(label_clamp, K, lengths)

        # 3. Build the model with initial params + label clamp.
        cls = _CLASS_BY_EMISSION[topology.emission.type]
        kwargs = _hmmlearn_kwargs(topology, seed=seed)
        model = cls(transmat_mask=mask, **kwargs)
        model.startprob_ = initial_startprob
        model.transmat_ = initial_transmat
        for key, val in emission_kwargs.items():
            setattr(model, key, val)
        # Do not let hmmlearn re-init from defaults during the EM run.
        model.init_params = ""
        # Injected — the overridden _compute_log_likelihood clamps -inf at
        # labelled positions, forcing forward-backward to act like argmax
        # there. When lengths is set, hmmlearn calls _compute_log_likelihood
        # once per sub-sequence; we pre-split the clamp and let the model's
        # cursor (reset in _estep_begin) advance through the segments.
        model._label_clamp = label_clamp
        if lengths is not None:
            segments: list[np.ndarray] = []
            offset = 0
            for L in lengths:
                segments.append(label_clamp[offset : offset + L])
                offset += L
            model._label_clamp_segments = segments
        else:
            model._label_clamp_segments = None
        model._label_clamp_cursor = [0]

        # 4. Run constrained EM (hmmlearn's standard .fit() respects the
        # clamp via our subclass override).
        if lengths is not None:
            model.fit(X, lengths=lengths)
        else:
            model.fit(X)

        # 5. Score on the unclamped likelihood (clear the clamp so the
        # reported log-likelihood reflects the data, not the constraint).
        model._label_clamp = None
        model._label_clamp_segments = None
        model._label_clamp_cursor = [0]
        log_lik = float(model.score(X, lengths=lengths))

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
            convergence_history=tuple(float(x) for x in getattr(monitor, "history", []) or []),
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
        from sklearn.mixture import GaussianMixture

        D = e.n_features
        M = e.n_mix
        X2 = X.reshape(-1, D)
        weights = np.zeros((K, M))
        means = np.zeros((K, M, D))
        covars_shape = _gmm_covars_shape(e.covariance_type, K, M, D)
        covars = np.zeros(covars_shape)
        for k in range(K):
            pts = X2[states == k]
            if len(pts) >= M:
                gm = GaussianMixture(
                    n_components=M,
                    covariance_type=e.covariance_type,
                    random_state=42,
                    reg_covar=1e-6,
                )
                gm.fit(pts)
                weights[k] = gm.weights_
                means[k] = gm.means_
                # sklearn returns the same shape hmmlearn expects per state
                # (M, D) / (M, D, D) / (M,) / (D, D) for tied.
                covars[k] = gm.covariances_
            else:
                # Degenerate path: not enough labelled points for M mixtures.
                # Fall back to uniform weights, repeat the per-state mean
                # (zero if no points), identity covar.
                weights[k] = np.full(M, 1.0 / M)
                mean_k = pts.mean(axis=0) if len(pts) > 0 else np.zeros(D)
                means[k] = np.broadcast_to(mean_k, (M, D)).copy()
                covars[k] = _gmm_identity_covars(e.covariance_type, M, D)
        return {"weights_": weights, "means_": means, "covars_": covars}

    raise ValueError(f"unknown emission type for supervised MLE: {e.type!r}")


def _gmm_covars_shape(covariance_type: str, K: int, M: int, D: int) -> tuple[int, ...]:
    """Return the per-state covariance array shape hmmlearn's GMMHMM expects."""
    if covariance_type == "full":
        return (K, M, D, D)
    if covariance_type == "diag":
        return (K, M, D)
    if covariance_type == "tied":
        # Tied across mixtures within a state: one (D, D) per state.
        return (K, D, D)
    if covariance_type == "spherical":
        return (K, M)
    raise ValueError(f"unknown covariance_type: {covariance_type!r}")


def _gmm_identity_covars(covariance_type: str, M: int, D: int) -> np.ndarray:
    """Return an identity-like covariance block for a single state's fallback path."""
    if covariance_type == "full":
        return np.broadcast_to(np.eye(D), (M, D, D)).copy()
    if covariance_type == "diag":
        return np.ones((M, D))
    if covariance_type == "tied":
        return np.eye(D)
    if covariance_type == "spherical":
        return np.ones(M)
    raise ValueError(f"unknown covariance_type: {covariance_type!r}")


# ---------------------------------------------------------------------------
# Semi-supervised helpers (Phase A.7.1)
# ---------------------------------------------------------------------------


def _validate_labelled_transitions(
    label_clamp: np.ndarray,
    mask: np.ndarray,
    lengths: np.ndarray | None,
) -> None:
    """Raise ValueError if any adjacent (labelled, labelled) edge is forbidden.

    Adjacent here means two consecutive timesteps WITHIN the same sub-sequence
    where both labels are known. Pairs separated by an unlabelled position are
    skipped — EM is free to route through any allowed path there.
    """
    bad: list[tuple[int, int]] = []
    for t, t1 in _iter_within_sequence(len(label_clamp), lengths):
        a, b = int(label_clamp[t]), int(label_clamp[t1])
        if a >= 0 and b >= 0 and not mask[a, b]:
            bad.append((a, b))
    if bad:
        seen: list[tuple[int, int]] = []
        for pair in bad:
            if pair not in seen:
                seen.append(pair)
            if len(seen) >= 5:
                break
        examples = ", ".join(f"{i}->{j}" for i, j in seen)
        raise ValueError(
            f"observed transitions violate topology mask "
            f"(forbidden edges observed: {examples}). "
            f"Either fix the labels or relax the topology's allowed_transitions."
        )


def _semi_supervised_initial_transmat(
    label_clamp: np.ndarray,
    K: int,
    mask: np.ndarray,
    lengths: np.ndarray | None,
) -> np.ndarray:
    """Initial transmat from counts on adjacent (labelled, labelled) pairs only.

    Transitions adjacent to unlabelled positions are NOT counted (EM will
    discover them). Empty rows fall back to uniform over allowed edges.
    """
    counts = np.zeros((K, K))
    for t, t1 in _iter_within_sequence(len(label_clamp), lengths):
        a, b = int(label_clamp[t]), int(label_clamp[t1])
        if a >= 0 and b >= 0:
            counts[a, b] += 1
    # Tiny pseudo-count on allowed edges so empty rows don't sum to zero.
    counts = counts + 1e-6 * mask.astype(float)
    return _apply_mask(counts, mask)


def _semi_supervised_initial_startprob(
    label_clamp: np.ndarray,
    K: int,
    lengths: np.ndarray | None,
) -> np.ndarray:
    """Initial startprob from labelled sequence-start positions only.

    If a sequence starts on an unlabelled position, it is skipped. If no
    sequence has a labelled first position, fall back to uniform.
    """
    starts: list[int] = []
    if lengths is None:
        if label_clamp[0] >= 0:
            starts.append(int(label_clamp[0]))
    else:
        offset = 0
        for L in lengths:
            if label_clamp[offset] >= 0:
                starts.append(int(label_clamp[offset]))
            offset += L
    if not starts:
        return np.full(K, 1.0 / K)
    sp = np.bincount(starts, minlength=K).astype(float)
    sp = sp + 1e-10
    sp /= sp.sum()
    return sp
