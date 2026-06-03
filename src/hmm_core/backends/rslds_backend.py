"""rSLDS backend for hmm_core — Phase D spike.

Wraps Linderman's ssm.SLDS (and optionally an Elastic-Net shim) behind the
HMMBackend protocol. Requires the [rslds] extra :
    pip install "hmm-studio[rslds]"
or run inside tools/docker/rslds.Dockerfile.

Heavy imports (ssm, sklearn) are deferred to inside RSLDSBackend.fit() and the
shim so referencing the module without using the backend pays no cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable
import warnings

import numpy as np

from hmm_core.backends._protocol import BackendFitResult

if TYPE_CHECKING:
    from hmm_core.topology import Topology


# ---------------------------------------------------------------------------
# Fitted-model adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RSLDSMonitor:
    """hmmlearn-style monitor adapter exposed by RSLDSFittedBundle.monitor_.

    Holds the ELBO trajectory and a coarse convergence flag computed from the
    last three ELBOs (relative plateau < 1e-3)."""

    history: list[float]
    converged: bool


@dataclass(frozen=True)
class RSLDSFittedBundle:
    """Adapter wrapping a fitted ssm rSLDS model.

    Exposes BOTH rSLDS-native attributes (``dynamics_As``, ``emissions_Cs``,
    ``latent_states``) AND hmmlearn-shaped duck-type attributes (``transmat_``,
    ``startprob_``, ``predict``, ``predict_proba``, ``score``, ``monitor_``) so
    downstream code that bypasses the formal HMMBackend protocol
    (``io.save_model``, ``_repr_html_``, NHMM, ComparePage) continues to
    function. Every hmmlearn-shaped attribute documents its rSLDS-specific
    semantics in its docstring (e.g. ``score`` returns ELBO, not marginal LL)."""

    model: Any                 # the underlying ssm.SLDS or _ElasticNetRSLDSCompat
    q_train: Any               # SLDSStructuredMeanFieldVariationalPosterior on X_train
    D_latent: int
    regularize: str
    n_features: int
    K: int
    elbo_history: list[float] = field(default_factory=list)

    # ---- rSLDS-native surface -----------------------------------------

    @property
    def dynamics_As(self) -> np.ndarray:
        """Per-regime dynamics matrices, shape (K, D_latent, D_latent)."""
        return np.asarray(self.model.dynamics.As)

    @property
    def dynamics_bs(self) -> np.ndarray:
        """Per-regime affine offsets, shape (K, D_latent)."""
        return np.asarray(self.model.dynamics.bs)

    @property
    def emissions_Cs(self) -> np.ndarray:
        """Emission projection matrix, shape (n_features, D_latent)."""
        return np.asarray(self.model.emissions.Cs[0])

    @property
    def emissions_ds(self) -> np.ndarray:
        """Emission offset, shape (n_features,)."""
        return np.asarray(self.model.emissions.ds[0])

    @property
    def latent_states(self) -> np.ndarray:
        """Mean continuous latent trajectory from q_train, shape (T_train, D_latent)."""
        return np.asarray(self.q_train.mean_continuous_states[0])

    # ---- hmmlearn-shaped duck-type surface ----------------------------

    @property
    def transmat_(self) -> np.ndarray:
        """(K, K) posterior-mean discrete transition matrix over q_train timesteps.

        rSLDS uses RECURRENT transitions: the true transition matrix is
        time-varying and depends on x_{t-1}. This property returns the
        time-averaged posterior of those transitions — a USABLE summary but
        NOT a stationary transition matrix in the HMM sense. Use only for
        broad-stroke inspection."""
        triples = self.q_train.discrete_expectations
        # TODO(v0.1): np.stack requires every per-sequence Ezzp1 to share T-1.
        # When HMMBackend.lengths support lands for rSLDS, switch to a ragged
        # average (loop + per-pair accumulator) so unequal-length sequences work.
        Ezzp1_stack = np.stack([np.asarray(t[1]) for t in triples])  # (n_seq, T-1, K, K)
        Ezzp1_mean = Ezzp1_stack.mean(axis=(0, 1))                    # (K, K)
        row_sums = Ezzp1_mean.sum(axis=1, keepdims=True)
        return Ezzp1_mean / np.where(row_sums > 0, row_sums, 1.0)

    @property
    def startprob_(self) -> np.ndarray:
        """(K,) posterior-mean initial-state distribution from q_train."""
        Ez = np.asarray(self.q_train.discrete_expectations[0][0])     # (T, K)
        return Ez[0]

    @property
    def monitor_(self) -> _RSLDSMonitor:
        """hmmlearn-style monitor: .history (list of ELBOs) and .converged (bool)."""
        return _RSLDSMonitor(history=list(self.elbo_history), converged=self._converged)

    @property
    def _converged(self) -> bool:
        if len(self.elbo_history) < 3:
            return False
        last3 = self.elbo_history[-3:]
        rel = abs(last3[-1] - last3[-2]) / (abs(last3[-2]) + 1e-9)
        return rel < 1e-3

    # predict / predict_proba / score delegate to RSLDSBackend static helpers
    # (added in Task 7).

    def predict(self, X: np.ndarray, lengths=None) -> np.ndarray:
        """Most-likely discrete state path = argmax of E-step posterior on X."""
        return RSLDSBackend._decode_static(self, X)

    def predict_proba(self, X: np.ndarray, lengths=None) -> np.ndarray:
        """(T, K) posterior over discrete states from E-step inference on X."""
        return RSLDSBackend._predict_proba_static(self, X)

    def score(self, X: np.ndarray, lengths=None) -> float:
        """ELBO on X via E-step-only inference. **NOT a marginal log-likelihood**.

        rSLDS marginal likelihood is intractable; we return the ELBO, which is
        a variational lower bound. Do NOT compare across backends (the
        hmmlearn ``score`` returns the exact marginal LL). Use only for
        relative comparison between rSLDS fits with the same topology."""
        return RSLDSBackend._score_static(self, X)


class RSLDSBackend:
    """rSLDS backend — name='rslds'. See module docstring."""

    name = "rslds"

    def __init__(self, regularize: str = "none") -> None:
        if regularize not in {"none", "elastic_net"}:
            raise ValueError(
                f"regularize must be 'none' or 'elastic_net', got {regularize!r}"
            )
        self.regularize = regularize
        self._warned_progress_callback = False

    def fit(self, topology, X, *, seed, lengths=None,
            initial_transmat, initial_startprob, emission_kwargs, mask,
            progress_callback=None, transmat_prior=None) -> BackendFitResult:
        """Fit an rSLDS via ssm Laplace-EM.

        Notes on protocol parameters that rSLDS does NOT honour in the spike :
        ``lengths``, ``initial_transmat``, ``initial_startprob``,
        ``emission_kwargs``, ``mask``, ``progress_callback``, ``transmat_prior``
        are accepted for HMMBackend conformance but currently IGNORED. rSLDS
        uses recurrent (input-dependent) transitions and a continuous latent —
        the discrete-transmat / discrete-mask / per-state emission concepts do
        not map. The bundle's ``transmat_`` is a POSTERIOR-MEAN summary, not a
        constraint. Tracked for v0.1."""
        if progress_callback is not None and not self._warned_progress_callback:
            warnings.warn(
                "RSLDSBackend ignores progress_callback in spike v0 — the rSLDS "
                "Laplace-EM does not stream per-iteration progress yet. Tracked "
                "for v0.1.",
                UserWarning,
                stacklevel=2,
            )
            self._warned_progress_callback = True

        K = topology.n_states
        n_features = X.shape[1]
        # ssm.SLDS uses orthogonal emissions by default — they require N > D
        # with D >= 1. With n_features < 2 there is no valid D_latent, so the
        # downstream ssm constructor would crash with a cryptic "shape (N, D)
        # not orthogonal" error far from the cause. Surface a clear ValueError
        # here so the user knows to pass at least 2 features.
        if n_features < 2:
            raise ValueError(
                f"RSLDSBackend.fit requires X to have at least 2 features "
                f"(got n_features={n_features}). ssm orthogonal emissions need "
                f"N > D where D >= 1; with N < 2 there is no valid latent dim."
            )

        import ssm  # heavy, deferred

        D_latent = max(1, min(K, n_features - 1))  # ssm orthogonal-emissions: N > D

        np.random.seed(seed)
        if self.regularize == "none":
            model = ssm.SLDS(
                n_features, K, D_latent,
                transitions="recurrent_only",
            )
        else:  # elastic_net
            model = _build_elastic_net_rslds(
                n_features, K, D_latent, alpha=0.05, l1_ratio=0.5,
            )

        q = ssm.variational.SLDSStructuredMeanFieldVariationalPosterior(model, X)
        # ssm.SLDS.fit returns (elbos, posterior). We supplied `q`; the returned
        # posterior is the same object (in-place updates), so we keep `q`.
        elbos, _ = model.fit(
            X, variational_posterior=q,
            method="laplace_em",
            num_iters=topology.fit.n_iter,
        )

        bundle = RSLDSFittedBundle(
            model=model,
            q_train=q,
            D_latent=D_latent,
            regularize=self.regularize,
            n_features=n_features,
            K=K,
            elbo_history=[float(e) for e in np.asarray(elbos).ravel()],
        )

        return BackendFitResult(
            model=bundle,
            transmat=bundle.transmat_,
            startprob=bundle.startprob_,
            log_likelihood=float(elbos[-1]),  # ELBO (caveat in bundle.score docstring)
            # ssm's _fit_laplace_em runs exactly num_iters Laplace-EM updates and
            # additionally records an initial ELBO before the first update — so
            # len(elbos) == num_iters + 1. We report num_iters as the count of
            # actual EM iterations to match hmmlearn semantics; the full ELBO
            # history (including the initial value) is exposed on the bundle.
            n_iter_actual=topology.fit.n_iter,
            converged=bundle._converged,
        )

    def fit_supervised(self, topology, X, states, *, seed, lengths=None,
                       mask) -> BackendFitResult:
        raise NotImplementedError(
            "rslds backend does not yet support fit_supervised "
            "(spike v0; tracked for v0.1)"
        )

    def decode(self, model, X, lengths=None) -> np.ndarray:
        """Most-likely discrete state path via E-step inference on X.

        ``model`` must be an :class:`RSLDSFittedBundle`."""
        return RSLDSBackend._decode_static(model, X)

    def predict_proba(self, model, X, lengths=None) -> np.ndarray:
        """(T, K) posterior over discrete states from E-step inference on X."""
        return RSLDSBackend._predict_proba_static(model, X)

    def score(self, model, X, lengths=None) -> float:
        """ELBO on X via E-step-only inference. NOT a marginal log-likelihood.

        rSLDS marginal likelihood is intractable; this returns the ELBO (a
        variational lower bound). Do NOT compare across backends — hmmlearn's
        ``score`` returns the exact marginal log-likelihood. Use only for
        relative comparison between rSLDS fits with the same topology."""
        return RSLDSBackend._score_static(model, X)

    # ---- Static helpers (also used by RSLDSFittedBundle's hmmlearn-duck face) ----

    @staticmethod
    def _infer_posterior_on(bundle: "RSLDSFittedBundle", X: np.ndarray, *,
                            infer_iters: int = 10) -> Any:
        """E-step-only inference : fit a fresh posterior on X with model params frozen.

        Calls ``model._fit_laplace_em`` directly (bypassing ``fit()`` which would
        re-initialize parameters) with ``learning=False``."""
        import ssm  # noqa: F401  (the import is needed to ensure ssm symbols resolve)

        model = bundle.model
        q_X = ssm.variational.SLDSStructuredMeanFieldVariationalPosterior(model, X)
        M = (int(model.M),) if np.isscalar(model.M) else tuple(model.M)
        inputs = [np.zeros((X.shape[0],) + M)]
        masks = [np.ones_like(X, dtype=bool)]
        tags = [None]
        model._fit_laplace_em(
            q_X, [X], inputs=inputs, masks=masks, tags=tags,
            num_iters=infer_iters, learning=False, verbose=0,
        )
        return q_X

    @staticmethod
    def _predict_proba_static(bundle: "RSLDSFittedBundle", X: np.ndarray) -> np.ndarray:
        q_X = RSLDSBackend._infer_posterior_on(bundle, X)
        Ez = np.asarray(q_X.discrete_expectations[0][0])  # (T, K)
        return Ez

    @staticmethod
    def _decode_static(bundle: "RSLDSFittedBundle", X: np.ndarray) -> np.ndarray:
        return RSLDSBackend._predict_proba_static(bundle, X).argmax(axis=1).astype(int)

    @staticmethod
    def _score_static(bundle: "RSLDSFittedBundle", X: np.ndarray) -> float:
        model = bundle.model
        q_X = RSLDSBackend._infer_posterior_on(bundle, X)
        M = (int(model.M),) if np.isscalar(model.M) else tuple(model.M)
        inputs = [np.zeros((X.shape[0],) + M)]
        masks = [np.ones_like(X, dtype=bool)]
        tags = [None]
        elbo = model._laplace_em_elbo(q_X, [X], inputs, masks, tags)
        return float(elbo)


# ---------------------------------------------------------------------------
# Elastic-Net rSLDS compatibility shim
#
# Nathan's research class ``ElasticNetRSLDS`` (in
# Projet_Robin/ssm_extensions.py of the sibling crypto repo) was written for an
# older ssm vintage where the hook ``_fit_laplace_em_params_update`` received
# ``(discrete_expectations, continuous_expectations, datas, ...)``. The ssm
# commit we pin (eb6c8aa) calls the hook with ``(variational_posterior, datas,
# ...)`` and computes the expectations internally. We bypass Nathan's broken
# override by going straight to SLDS' standard m-step, then run his elastic-net
# m-step with the expectations extracted from the posterior. Sub-project A
# implemented this same shim (as _BenchmarkRSLDS) in
# Projet_Robin/benchmark/models.py — we port that here verbatim.
# ---------------------------------------------------------------------------


def _build_elastic_net_rslds(N: int, K: int, D: int, *, alpha: float = 0.05,
                             l1_ratio: float = 0.5):
    """Construct the Elastic-Net rSLDS shim instance.

    Imports are LAZY because :
      - ssm is only present in the [rslds] extra ;
      - the Elastic-Net class lives in Nathan's sibling repo
        Projet_Robin/ssm_extensions.py, which must be importable.

    Raises ImportError with an actionable message if either is missing.
    """
    try:
        import ssm
    except ImportError as exc:  # pragma: no cover - covered by [rslds] extra gating
        raise ImportError(
            "RSLDSBackend(regularize='elastic_net') requires ssm: "
            "pip install \"hmm-studio[rslds]\""
        ) from exc
    try:
        from ssm_extensions import ElasticNetRSLDS  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "RSLDSBackend(regularize='elastic_net') requires Nathan's "
            "ssm_extensions module (Projet_Robin/ssm_extensions.py) on the "
            "Python path. Plain regularize='none' does not need it."
        ) from exc

    class _ElasticNetRSLDSCompat(ElasticNetRSLDS):
        """Shim against ssm commit eb6c8aa. See _build_elastic_net_rslds docstring."""

        def fit(self, datas, *args, method: str = "laplace_em", **kwargs):
            if method != "laplace_em":
                raise ValueError(
                    "_ElasticNetRSLDSCompat only supports method='laplace_em'"
                )
            return super().fit(datas, *args, method=method, **kwargs)

        def _fit_laplace_em_params_update(
            self, variational_posterior, datas, inputs, masks, tags,
            emission_optimizer, emission_optimizer_maxiter, alpha,
        ):
            # super(ElasticNetRSLDS, self) resolves the next class AFTER
            # ElasticNetRSLDS in our MRO — same effect as the explicit
            # `ssm.SLDS.<method>(self, ...)` call, but it correctly follows MRO
            # if any future class is inserted between _ElasticNetRSLDSCompat and
            # SLDS (other than ElasticNetRSLDS, which we deliberately skip).
            super(ElasticNetRSLDS, self)._fit_laplace_em_params_update(
                variational_posterior, datas, inputs, masks, tags,
                emission_optimizer, emission_optimizer_maxiter, alpha,
            )
            continuous_expectations = variational_posterior.mean_continuous_states
            discrete_expectations = variational_posterior.discrete_expectations
            self._elastic_net_m_step(continuous_expectations, discrete_expectations)

    return _ElasticNetRSLDSCompat(
        N, K, D, alpha=alpha, l1_ratio=l1_ratio, transitions="recurrent_only"
    )
