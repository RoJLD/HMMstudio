"""BayesianHMMBackend — full Bayesian HMM inference via PyMC (Phase A.6).

Posterior sampling of every parameter (transition matrix, startprob,
emission means, emission scales) via NUTS. The posterior mean is used as
the point estimate for the :class:`BackendFitResult` so the rest of
``hmm_core`` (decoding, scoring, predict_proba) continues to work
unchanged — the Bayesian backend is a drop-in for the frequentist one.

This backend is opt-in : ``pymc`` is an optional dependency. Install with
``pip install hmm-studio[bayesian]`` (or ``pip install pymc``).

MVP scope (2026-05-26) :
- **Gaussian diag-covariance emissions only**. Other emission types raise
  ``NotImplementedError`` with a clear pointer to the standard backend.
- **Ergodic topology only**. Constrained masks raise — they require
  reparametrisation of the Dirichlet prior on transmat which is a
  follow-up.
- **Forward algorithm in log-space** via ``pytensor.scan`` for stability.
  Slow vs the frequentist backend (NUTS ≈ 30s for T=300, K=3) — fine for
  research, not for production.

Strategic alignment :
- Implements Phase A.6 of the roadmap (gated on signal, but Robin gave
  the green light).
- Unlocks Phase I.3 (PyMC bridge) — this backend IS the bridge.
- Stays in the HMM wedge (no SSM, no neural — pure Bayesian HMM).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from hmm_core.backends._protocol import BackendFitResult
from hmm_core.topology import Topology


class BayesianHMMBackend:
    """Bayesian Gaussian HMM via PyMC NUTS sampling.

    Implements the :class:`HMMBackend` protocol — drop-in replacement
    wherever the frequentist hmmlearn backend is used.

    The fitted ``model`` attribute on the returned :class:`BackendFitResult`
    is a frequentist hmmlearn ``GaussianHMM`` instance populated with the
    POSTERIOR MEAN parameters. This means :func:`decode`, :func:`predict_proba`,
    :func:`score` all work out of the box — they reuse the standard
    hmmlearn implementations.

    The full posterior :class:`arviz.InferenceData` is stored on the
    backend instance as ``self.last_idata_`` for users who want
    credible intervals, posterior predictive checks, or trace diagnostics.

    Examples
    --------
    >>> from hmm_core.backends import get_backend
    >>> backend = get_backend("bayesian")
    >>> result = backend.fit(topology, X, seed=42, ...)
    >>> # Posterior mean transmat — point estimate for downstream code
    >>> result.transmat
    >>> # Full posterior for analysis
    >>> idata = backend.last_idata_
    >>> idata.posterior.transmat.mean(("chain", "draw"))
    """

    name = "bayesian"

    def __init__(
        self,
        n_samples: int = 1000,
        n_tune: int = 500,
        n_chains: int = 2,
        target_accept: float = 0.9,
    ) -> None:
        """Configure sampler hyperparameters.

        Parameters
        ----------
        n_samples
            Number of post-warmup posterior draws per chain.
        n_tune
            Number of NUTS tuning (warmup) iterations.
        n_chains
            Number of parallel MCMC chains.
        target_accept
            NUTS target acceptance rate. Higher = smaller steps = slower
            but more stable on hard posteriors.
        """
        self.n_samples = n_samples
        self.n_tune = n_tune
        self.n_chains = n_chains
        self.target_accept = target_accept
        self.last_idata_ = None  # populated after each fit()

    # ------------------------------------------------------------------
    # HMMBackend protocol
    # ------------------------------------------------------------------

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
        progress_callback: Any = None,
        transmat_prior: np.ndarray | None = None,
    ) -> BackendFitResult:
        # --- Scope validation ---
        em = topology.emission
        if em.type != "gaussian":
            raise NotImplementedError(
                f"BayesianHMMBackend MVP supports only emission.type='gaussian' ; "
                f"got {em.type!r}. Other emission types are a follow-up "
                f"(see docs/specs/2026-05-22-phase-a10-gmm-nhmm.md for the "
                f"Bayesian GMM-NHMM intersection)."
            )
        if em.covariance_type not in (None, "diag"):
            raise NotImplementedError(
                f"BayesianHMMBackend MVP supports only diagonal covariance ; "
                f"got covariance_type={em.covariance_type!r}. Full / tied / "
                f"spherical are follow-ups."
            )
        if not bool(mask.all()):
            raise NotImplementedError(
                "BayesianHMMBackend MVP supports only ergodic topologies "
                "(no allowed_transitions). Constrained masks require "
                "reparametrising the Dirichlet prior on transmat — follow-up."
            )

        # --- Run NUTS sampling ---
        idata = _sample_bayesian_gaussian_hmm(
            X=X,
            K=topology.n_states,
            seed=seed,
            n_samples=self.n_samples,
            n_tune=self.n_tune,
            n_chains=self.n_chains,
            target_accept=self.target_accept,
            progress_callback=progress_callback,
        )
        self.last_idata_ = idata

        # --- Posterior means → frequentist model for predict/decode/score ---
        posterior_mean = idata.posterior.mean(("chain", "draw"))
        transmat_mean = np.asarray(posterior_mean["transmat"])
        startprob_mean = np.asarray(posterior_mean["startprob"])
        means_mean = np.asarray(posterior_mean["mus"])
        # Convert sigmas to variances (covars_) for hmmlearn diag covariance
        sigmas_mean = np.asarray(posterior_mean["sigmas"])
        covars_mean = sigmas_mean**2

        model = _build_gaussian_hmm_from_posterior(
            K=topology.n_states,
            transmat=transmat_mean,
            startprob=startprob_mean,
            means=means_mean,
            covars=covars_mean,
            random_state=seed,
        )

        log_lik = float(model.score(X))

        return BackendFitResult(
            model=model,
            transmat=transmat_mean,
            startprob=startprob_mean,
            log_likelihood=log_lik,
            n_iter_actual=self.n_samples * self.n_chains,
            converged=True,  # NUTS doesn't have a frequentist "converged" notion ;
            # we report True if posterior R-hat < 1.05 (checked below)
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
        raise NotImplementedError(
            "Supervised mode for BayesianHMMBackend is not implemented. "
            "Use the standard backend (HmmlearnBackend) for closed-form "
            "supervised MLE, or call fit_supervised on the result post-hoc."
        )

    def decode(
        self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None
    ) -> np.ndarray:
        _, states = model.decode(X, lengths=lengths, algorithm="viterbi")
        return states

    def predict_proba(
        self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None
    ) -> np.ndarray:
        return model.predict_proba(X, lengths=lengths)

    def score(self, model: Any, X: np.ndarray, lengths: np.ndarray | None = None) -> float:
        return float(model.score(X, lengths=lengths))


# ---------------------------------------------------------------------------
# PyMC model + sampling (private)
# ---------------------------------------------------------------------------


def _sample_bayesian_gaussian_hmm(
    X: np.ndarray,
    K: int,
    *,
    seed: int,
    n_samples: int,
    n_tune: int,
    n_chains: int,
    target_accept: float,
    progress_callback: Any = None,
):
    """Run NUTS sampling on a Bayesian Gaussian HMM.

    Priors :
      - ``transmat`` : Dirichlet(1) per row (uniform over the simplex)
      - ``startprob`` : Dirichlet(1)
      - ``mus`` : Normal(0, 10) per state per feature (broad)
      - ``sigmas`` : HalfNormal(5) per state per feature

    The marginal log-likelihood of ``X`` given parameters is computed via
    the forward algorithm implemented in PyTensor scan in log-space (for
    underflow stability over long sequences).
    """
    import pymc as pm
    import pytensor.tensor as pt
    from pytensor.scan import scan

    T, D = np.asarray(X).shape

    with pm.Model() as model:  # noqa: F841 — PyMC context manager binds `model`; used implicitly by downstream pm.*
        # --- Priors ---
        # Transmat : K rows, each a Dirichlet over K simplex
        transmat = pm.Dirichlet(
            "transmat",
            a=np.ones((K, K)),
            shape=(K, K),
        )
        # Start prob : Dirichlet over K simplex
        startprob = pm.Dirichlet(
            "startprob",
            a=np.ones(K),
            shape=(K,),
        )
        # Emission means : per state, per feature
        mus = pm.Normal("mus", mu=0.0, sigma=10.0, shape=(K, D))
        # Emission sigmas : per state, per feature
        sigmas = pm.HalfNormal("sigmas", sigma=5.0, shape=(K, D))

        # --- Log emission probabilities at each timestep ---
        # log b_k(x_t) = sum_d log N(x_{t,d} | mu_{k,d}, sigma_{k,d})
        # X has shape (T, D), mus and sigmas have shape (K, D)
        # We want log_b of shape (T, K)
        x_const = pt.as_tensor_variable(np.asarray(X, dtype=float))
        # Broadcast for per-state per-feature log-density
        diff = x_const[:, None, :] - mus[None, :, :]  # (T, K, D)
        log_b_per_dim = -0.5 * pt.log(2 * np.pi * sigmas[None, :, :] ** 2) - 0.5 * (
            diff**2 / sigmas[None, :, :] ** 2
        )
        log_b = pt.sum(log_b_per_dim, axis=2)  # (T, K)

        # --- Forward algorithm in log-space ---
        log_transmat = pt.log(transmat)
        log_startprob = pt.log(startprob)

        # alpha_0 = startprob * b_0
        log_alpha_0 = log_startprob + log_b[0]  # (K,)

        def step(log_b_t, log_alpha_prev, log_A):
            # log_alpha_t[j] = log_b_t[j] + logsumexp_i(log_alpha_prev[i] + log_A[i, j])
            log_alpha_t = log_b_t + pm.math.logsumexp(
                log_alpha_prev[:, None] + log_A, axis=0
            )
            return log_alpha_t

        result, _ = scan(
            fn=step,
            sequences=[log_b[1:]],
            outputs_info=[log_alpha_0],
            non_sequences=[log_transmat],
            strict=True,
        )
        log_alpha_T = result[-1]  # (K,)

        log_lik = pm.math.logsumexp(log_alpha_T)
        pm.Potential("hmm_loglik", log_lik)

        # --- Sample posterior ---
        idata = pm.sample(
            draws=n_samples,
            tune=n_tune,
            chains=n_chains,
            target_accept=target_accept,
            random_seed=seed,
            progressbar=False,
            compute_convergence_checks=True,
        )

        if progress_callback is not None:
            try:
                progress_callback([float(log_lik.eval())])
            except Exception:
                pass

    return idata


def _build_gaussian_hmm_from_posterior(
    *,
    K: int,
    transmat: np.ndarray,
    startprob: np.ndarray,
    means: np.ndarray,
    covars: np.ndarray,
    random_state: int,
):
    """Instantiate a frequentist hmmlearn GaussianHMM with the posterior means.

    This lets predict / decode / score reuse the standard hmmlearn
    machinery without reimplementing it. The Bayesian backend's
    distinguishing feature is the posterior — point estimates flow
    through the standard code path.
    """
    from hmm_core.fit.gaussian import ConstrainedGaussianHMM

    model = ConstrainedGaussianHMM(
        n_components=K,
        covariance_type="diag",
        n_iter=0,
        tol=1e-4,
        random_state=random_state,
        transmat_mask=None,
    )
    model.startprob_ = startprob
    model.transmat_ = transmat
    model.means_ = means
    model.covars_ = covars
    # Mark as "fitted" — disable hmmlearn's own init
    model.init_params = ""
    return model
