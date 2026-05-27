"""HMMClassifier — sklearn-compatible HMM estimator (Phase I.2).

Implements the scikit-learn ``BaseEstimator`` + ``ClassifierMixin`` contract :
- ``__init__`` accepts only simple parameters (no Topology object) — sklearn
  introspects these for ``get_params`` / ``set_params`` / ``clone``.
- ``fit(X, y=None)`` — supervised if ``y`` is provided (closed-form MLE via
  ``fit_supervised``), else unsupervised Baum-Welch.
- ``predict(X)`` — Viterbi MAP state sequence.
- ``predict_proba(X)`` — forward-backward smoothed posteriors.
- ``score(X, y=None)`` — accuracy if ``y`` provided (ClassifierMixin
  semantics), else log-likelihood per timestep.
- Fitted attributes end with ``_`` (sklearn convention) :
  ``transmat_``, ``startprob_``, ``classes_``, ``n_iter_``, ``log_likelihood_``,
  ``bic_``, ``aic_``, ``converged_``.

Note : HMM has temporal semantics. ``cross_val_score`` with a random
``KFold`` splits sequences arbitrarily, which is statistically wrong for
HMM. Use ``TimeSeriesSplit`` if cross-validation is required.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_is_fitted


class HMMClassifier(BaseEstimator, ClassifierMixin):
    """scikit-learn compatible Hidden Markov Model classifier.

    Parameters
    ----------
    n_states : int, default=3
        Number of hidden states (K).
    emission_type : {"gaussian", "gmm", "multinomial", "poisson"}, default="gaussian"
        Type of emission distribution.
    covariance_type : {"full", "diag", "tied", "spherical"}, default="diag"
        Covariance type for gaussian / gmm emissions. Ignored for multinomial / poisson.
    n_features : int, default=1
        Observation dimension for gaussian / gmm / poisson. For multinomial
        observations, this should be 1 (single integer column).
    n_mix : int or None, default=None
        Number of mixture components for gmm. Required when emission_type="gmm".
    n_symbols : int or None, default=None
        Alphabet size for multinomial. Required when emission_type="multinomial".
    allowed_transitions : list of (str, str) or None, default=None
        Optional whitelist of allowed transitions ; pairs of state names.
        State names follow the convention ``["s0", "s1", ..., "s{n_states-1}"]``.
        ``None`` means ergodic (every transition allowed).
    startprob : str or list, default="uniform"
        Initial state distribution. ``"uniform"``, ``"first_state"``, or a
        list of K probabilities summing to 1.
    init_strategy : {"uniform", "random", "kmeans", "data_frequencies"}, default="kmeans"
        Parameter initialization strategy.
    init_seed : int, default=42
        Random seed for initialization and Baum-Welch.
    n_iter : int, default=100
        Maximum number of EM iterations.
    tol : float, default=1e-4
        Convergence tolerance on the log-likelihood.

    Attributes
    ----------
    transmat_ : ndarray of shape (n_states, n_states)
        Fitted transition matrix.
    startprob_ : ndarray of shape (n_states,)
        Fitted initial state distribution.
    classes_ : ndarray of shape (n_states,)
        Integer state labels ``[0, 1, ..., n_states-1]``.
    n_iter_ : int
        Number of EM iterations actually run.
    log_likelihood_ : float
        Log-likelihood of training data under the fitted model.
    bic_, aic_ : float
        Information criteria.
    converged_ : bool
        True if EM converged before reaching ``n_iter``.
    """

    def __init__(
        self,
        n_states: int = 3,
        emission_type: str = "gaussian",
        covariance_type: str = "diag",
        n_features: int = 1,
        n_mix: int | None = None,
        n_symbols: int | None = None,
        allowed_transitions: list[tuple[str, str]] | None = None,
        startprob: str | list[float] = "uniform",
        init_strategy: str = "kmeans",
        init_seed: int = 42,
        n_iter: int = 100,
        tol: float = 1e-4,
    ) -> None:
        # IMPORTANT for sklearn : __init__ only stores attributes, no logic.
        # All defaults match sklearn's get_params contract.
        self.n_states = n_states
        self.emission_type = emission_type
        self.covariance_type = covariance_type
        self.n_features = n_features
        self.n_mix = n_mix
        self.n_symbols = n_symbols
        self.allowed_transitions = allowed_transitions
        self.startprob = startprob
        self.init_strategy = init_strategy
        self.init_seed = init_seed
        self.n_iter = n_iter
        self.tol = tol

    # ------------------------------------------------------------------
    # sklearn protocol
    # ------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> "HMMClassifier":
        """Fit the HMM on observations ``X``.

        If ``y`` is provided (integer state labels), uses supervised closed-form
        MLE. Else, runs unsupervised Baum-Welch EM.
        """
        from hmm_core.fit import fit as core_fit
        from hmm_core.topology import (
            EmissionSpec,
            FitSpec,
            InitSpec,
            Topology,
        )

        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        # Build topology from sklearn-compatible parameters
        emission = EmissionSpec(
            type=self.emission_type,
            covariance_type=(
                self.covariance_type if self.emission_type in ("gaussian", "gmm") else None
            ),
            n_features=self.n_features,
            n_mix=self.n_mix,
            n_symbols=self.n_symbols,
        )
        topology = Topology(
            name="sklearn-compat",
            n_states=self.n_states,
            state_names=[f"s{i}" for i in range(self.n_states)],
            emission=emission,
            allowed_transitions=self.allowed_transitions,
            startprob=self.startprob,
            init=InitSpec(strategy=self.init_strategy, seed=self.init_seed),
            fit=FitSpec(algorithm="baum_welch", n_iter=self.n_iter, tol=self.tol),
        )

        if y is not None:
            y_int = np.asarray(y).astype(int)
            self.result_ = core_fit(topology, X, seed=self.init_seed, states=y_int)
        else:
            self.result_ = core_fit(topology, X, seed=self.init_seed)

        # sklearn-style fitted attributes
        self.topology_ = topology
        self.transmat_ = np.asarray(self.result_.model.transmat_)
        self.startprob_ = np.asarray(self.result_.model.startprob_)
        self.classes_ = np.arange(self.n_states)
        self.n_iter_ = self.result_.n_iter_actual
        self.log_likelihood_ = self.result_.log_likelihood
        self.bic_ = self.result_.bic
        self.aic_ = self.result_.aic
        self.converged_ = self.result_.converged
        self.n_features_in_ = X.shape[1]

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Viterbi MAP state sequence for the given observations."""
        check_is_fitted(self, "result_")
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return self.result_.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Forward-backward smoothed posteriors, shape (n_samples, n_states)."""
        check_is_fitted(self, "result_")
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return self.result_.model.predict_proba(X)

    def score(self, X: np.ndarray, y: np.ndarray | None = None) -> float:
        """Score on (X, y).

        - If ``y`` provided : mean classification accuracy (ClassifierMixin semantics).
        - Else : log-likelihood per timestep ``log P(X) / T``.
        """
        check_is_fitted(self, "result_")
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if y is None:
            return float(self.result_.model.score(X)) / max(len(X), 1)
        y_pred = self.predict(X)
        y = np.asarray(y).astype(int)
        return float((y_pred == y).mean())

    # ------------------------------------------------------------------
    # sklearn tags & metadata
    # ------------------------------------------------------------------

    def _more_tags(self) -> dict[str, Any]:
        # Tells sklearn that this estimator handles sequential data, not iid.
        # Helps avoid spurious failures in some estimator checks.
        return {
            "requires_y": False,  # y is optional (unsupervised mode)
            "X_types": ["2darray"],
            "_skip_test": False,
            "no_validation": False,
        }

    # ------------------------------------------------------------------
    # Rich display (delegates to FittedModel._repr_html_)
    # ------------------------------------------------------------------

    def _repr_html_(self) -> str:
        try:
            check_is_fitted(self, "result_")
        except Exception:
            # Not yet fitted — show a minimal representation
            from hmm_core._jupyter import render_stats_table, wrap_html

            params = self.get_params()
            return wrap_html(
                "<h4>HMMClassifier (not fitted)</h4>",
                render_stats_table(list(params.items())),
                '<div class="small">Call <code>.fit(X)</code> or '
                "<code>.fit(X, y)</code> to fit.</div>",
            )
        return self.result_._repr_html_()
