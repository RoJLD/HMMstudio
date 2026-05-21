"""Public fit() dispatcher and FittedModel container."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from hmm_core import init as init_mod
from hmm_core.fit.gaussian import ConstrainedGaussianHMM
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


_CLASS_BY_EMISSION = {
    "gaussian": ConstrainedGaussianHMM,
    # gmm, multinomial, poisson registered in T10-T12.
}


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
        cov_per = D if e.covariance_type == "diag" else D * (D + 1) // 2
        return transitions + K * M * (D + cov_per) + K * (M - 1)
    if e.type == "multinomial":
        return transitions + K * (e.n_symbols - 1)
    if e.type == "poisson":
        return transitions + K * e.n_features
    raise ValueError(f"unsupported emission type for n_params: {e.type!r}")


def _hmmlearn_kwargs(topology: Topology, seed: int) -> dict:
    """Map EmissionSpec -> constructor kwargs for hmmlearn class."""
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


def fit(topology: Topology, X: np.ndarray, *, seed: int | None = None) -> FittedModel:
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
    """
    topology.validate()
    actual_seed = seed if seed is not None else topology.init.seed

    if topology.emission.type not in _CLASS_BY_EMISSION:
        raise ValueError(
            f"unsupported emission: {topology.emission.type!r} "
            f"(supported: {sorted(_CLASS_BY_EMISSION)})"
        )

    mask = topology.transition_mask()
    initial_A = init_mod.transmat(topology, seed=actual_seed, X=X)
    initial_pi = init_mod.startprob(topology, seed=actual_seed)
    emission_kwargs = init_mod.emission_params(topology, X=X, seed=actual_seed)

    cls = _CLASS_BY_EMISSION[topology.emission.type]
    kwargs = _hmmlearn_kwargs(topology, seed=actual_seed)
    model = cls(transmat_mask=mask, **kwargs)
    # Pre-set parameters that init.* provides; skip the corresponding letters
    # in init_params so hmmlearn does not overwrite them.
    model.startprob_ = initial_pi
    model.transmat_ = initial_A
    skip_letters = "st"
    if emission_kwargs:
        for key, val in emission_kwargs.items():
            setattr(model, key, val)
        # Skip 'm' (means), 'c' (covars), 'w' (weights), 'e' (emissionprob),
        # 'l' (lambdas) according to what we pre-set.
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

    t0 = time.perf_counter()
    model.fit(X)
    duration = time.perf_counter() - t0

    log_lik = float(model.score(X))
    n_params = _n_params(topology.n_states, topology.emission)
    n_obs = len(X)
    bic = float(-2.0 * log_lik + n_params * np.log(max(n_obs, 1)))
    aic = float(-2.0 * log_lik + 2.0 * n_params)

    monitor = getattr(model, "monitor_", None)
    converged = bool(monitor.converged) if monitor is not None else False
    n_iter_actual = int(monitor.iter) if monitor is not None else topology.fit.n_iter

    return FittedModel(
        model=model,
        topology=topology,
        log_likelihood=log_lik,
        bic=bic,
        aic=aic,
        n_iter_actual=n_iter_actual,
        converged=converged,
        seed=actual_seed,
        duration_seconds=duration,
    )
