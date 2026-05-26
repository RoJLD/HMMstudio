"""Initialization strategies for constrained HMM fits.

All ``transmat`` strategies respect ``topology.transition_mask()`` by construction;
a final ``_apply_mask`` is used as a safety net.
"""

from __future__ import annotations

import numpy as np

from hmm_core.fit._base import _apply_mask
from hmm_core.topology import Topology


def transmat(
    topology: Topology,
    *,
    seed: int,
    X: np.ndarray | None = None,
    lengths: np.ndarray | None = None,
) -> np.ndarray:
    """Build an initial K x K transition matrix that respects the topology mask."""
    strategy = topology.init.strategy
    mask = topology.transition_mask()
    K = topology.n_states

    if strategy == "uniform":
        allowed_per_row = mask.sum(axis=1)
        A = mask.astype(float) / allowed_per_row[:, None]
        return _apply_mask(A, mask)

    if strategy == "random":
        rng = np.random.default_rng(seed)
        A = np.zeros((K, K))
        for i in range(K):
            allowed = np.where(mask[i])[0]
            draws = rng.dirichlet(np.ones(len(allowed)))
            A[i, allowed] = draws
        return _apply_mask(A, mask)

    if strategy in ("kmeans", "data_frequencies"):
        if X is None:
            raise ValueError(f"strategy={strategy!r} requires X (cannot init without data)")
        if strategy == "kmeans":
            # transmat stays uniform; kmeans only touches emissions.
            allowed_per_row = mask.sum(axis=1)
            A = mask.astype(float) / allowed_per_row[:, None]
            return _apply_mask(A, mask)
        # data_frequencies: pre-cluster X by kmeans, count transitions of
        # consecutive cluster labels, mask + normalize.
        from sklearn.cluster import KMeans

        km = KMeans(n_clusters=K, random_state=seed, n_init=10).fit(X)
        labels = km.labels_
        counts = np.zeros((K, K))
        if lengths is None:
            for t in range(len(labels) - 1):
                counts[labels[t], labels[t + 1]] += 1
        else:
            offset = 0
            for L in lengths:
                # Count transitions within this sequence only, skipping the
                # boundary into the next sequence.
                for t in range(offset, offset + L - 1):
                    counts[labels[t], labels[t + 1]] += 1
                offset += L
        # Symmetry breaker: add 1 to every allowed edge so rows can't be empty
        # after masking on a short / sparse cluster trajectory.
        counts = counts + mask.astype(float)
        return _apply_mask(counts, mask)

    raise ValueError(f"unknown init strategy: {strategy!r}")


def startprob(topology: Topology, *, seed: int) -> np.ndarray:
    K = topology.n_states
    sp = topology.startprob
    if sp == "uniform":
        return np.full(K, 1.0 / K)
    if sp == "first_state":
        out = np.zeros(K)
        out[0] = 1.0
        return out
    if isinstance(sp, list):
        return np.asarray(sp, dtype=float)
    raise ValueError(f"unknown startprob value: {sp!r}")


def emission_params(
    topology: Topology,
    X: np.ndarray | None,
    *,
    seed: int,
) -> dict[str, np.ndarray]:
    """Return dict of pre-set emission parameters.

    For Gaussian/GMM: ``means_`` and ``covars_``.
    For Multinomial: ``emissionprob_``.
    For Poisson: ``lambdas_``.

    Empty dict if the strategy does not pre-set emissions (uniform, random).

    A.8: If ``topology.emissions`` is set, per-state init hints override the
    base strategy results before returning.
    """
    strategy = topology.init.strategy
    if strategy in ("uniform", "random"):
        params: dict[str, np.ndarray] = {}
    elif strategy == "kmeans":
        if X is None:
            raise ValueError("kmeans emission init requires X")
        params = _kmeans_emission_params(topology, X, seed=seed)
    elif strategy == "data_frequencies":
        if X is None:
            raise ValueError("data_frequencies emission init requires X")
        # data_frequencies reuses the kmeans-based emission init.
        params = _kmeans_emission_params(topology, X, seed=seed)
    else:
        raise ValueError(f"unknown init strategy: {strategy!r}")

    return _apply_per_state_init_overrides(params, topology)


def _apply_per_state_init_overrides(
    params: dict[str, np.ndarray],
    topology: Topology,
) -> dict[str, np.ndarray]:
    """If ``topology.emissions`` is set, override per-state init hints into ``params``.

    A.8: applies init_mean, init_lambda, and init_emissionprob hints from
    each entry in ``topology.emissions`` to the corresponding row of the
    relevant parameter array.  Only affects states where a hint is present;
    states without hints keep whatever was computed by the base strategy.
    """
    if topology.emissions is None:
        return params

    K = topology.n_states
    e_type = topology.emission.type

    if e_type in ("gaussian", "gmm"):
        means_override = []
        any_override = False
        for k in range(K):
            hint = topology.emissions[k].init_mean
            if hint is not None:
                means_override.append(hint)
                any_override = True
            else:
                if "means_" in params:
                    if e_type == "gaussian":
                        means_override.append(list(params["means_"][k]))
                    else:
                        # gmm: shape (K, n_mix, D) — use first mixture component
                        means_override.append(list(params["means_"][k][0]))
                else:
                    means_override.append([0.0] * (topology.emission.n_features or 1))
        if any_override:
            arr = np.array(means_override, dtype=float)
            if e_type == "gaussian":
                params["means_"] = arr
            else:  # gmm: override first mixture component per state
                if "means_" in params and params["means_"].ndim == 3:
                    new = params["means_"].copy()
                    for k in range(K):
                        if topology.emissions[k].init_mean is not None:
                            new[k, 0] = arr[k]
                    params["means_"] = new

    elif e_type == "poisson":
        lambdas_override = []
        any_override = False
        for k in range(K):
            hint = topology.emissions[k].init_lambda
            if hint is not None:
                lambdas_override.append(hint)
                any_override = True
            else:
                if "lambdas_" in params:
                    lambdas_override.append(list(params["lambdas_"][k]))
                else:
                    lambdas_override.append([1.0] * (topology.emission.n_features or 1))
        if any_override:
            params["lambdas_"] = np.array(lambdas_override, dtype=float)

    elif e_type == "multinomial":
        ep_override = []
        any_override = False
        for k in range(K):
            hint = topology.emissions[k].init_emissionprob
            if hint is not None:
                ep_override.append(hint)
                any_override = True
            else:
                if "emissionprob_" in params:
                    ep_override.append(list(params["emissionprob_"][k]))
                else:
                    n = topology.emission.n_symbols or 2
                    ep_override.append([1.0 / n] * n)
        if any_override:
            arr = np.array(ep_override, dtype=float)
            arr /= arr.sum(axis=1, keepdims=True)
            params["emissionprob_"] = arr

    return params


def _kmeans_emission_params(
    topology: Topology,
    X: np.ndarray,
    *,
    seed: int,
) -> dict[str, np.ndarray]:
    from sklearn.cluster import KMeans

    K = topology.n_states
    e = topology.emission

    if e.type == "gaussian":
        km = KMeans(n_clusters=K, random_state=seed, n_init=10).fit(X)
        means_ = km.cluster_centers_
        covars_ = _empirical_covars(X, km.labels_, K, e.covariance_type)
        return {"means_": means_, "covars_": covars_}

    if e.type == "gmm":
        # For GMM init: per state, fit k=n_mix sub-kmeans (means + per-mode covars).
        # Returns means_ (K, n_mix, D), covars_ in the shape hmmlearn's GMMHMM
        # expects for the requested covariance_type:
        #   - "diag"      -> (K, n_mix, D)
        #   - "full"      -> (K, n_mix, D, D)
        #   - "tied"      -> (K, D, D)         (one (D, D) per state, shared across mixtures)
        #   - "spherical" -> (K, n_mix)
        # weights_ -> (K, n_mix), uniform.
        km = KMeans(n_clusters=K, random_state=seed, n_init=10).fit(X)
        D = X.shape[1]
        M = e.n_mix
        cov_type = e.covariance_type
        means_ = np.zeros((K, M, D))
        weights_ = np.ones((K, M)) / M

        if cov_type == "full":
            covars_ = np.zeros((K, M, D, D))
        elif cov_type == "tied":
            covars_ = np.zeros((K, D, D))
        elif cov_type == "spherical":
            covars_ = np.zeros((K, M))
        else:  # "diag" — original path
            covars_ = np.zeros((K, M, D))

        for k in range(K):
            cluster_X = X[km.labels_ == k]
            if len(cluster_X) < M:
                # Degenerate state: not enough points to fit M sub-mixtures.
                means_[k] = km.cluster_centers_[k]
                if cov_type == "full":
                    for m in range(M):
                        covars_[k, m] = np.eye(D)
                elif cov_type == "tied":
                    covars_[k] = np.eye(D)
                elif cov_type == "spherical":
                    covars_[k] = 1.0
                else:  # diag
                    covars_[k] = 1.0
                continue

            sub = KMeans(n_clusters=M, random_state=seed, n_init=5).fit(cluster_X)
            means_[k] = sub.cluster_centers_

            if cov_type == "tied":
                # One (D, D) covariance per state, shared across all mixtures.
                if len(cluster_X) > 1:
                    C = np.cov(cluster_X, rowvar=False)
                    C = 0.5 * (C + C.T) + 1e-6 * np.eye(D)
                    covars_[k] = C
                else:
                    covars_[k] = np.eye(D)
                continue

            for m in range(M):
                sub_pts = cluster_X[sub.labels_ == m]
                if cov_type == "full":
                    if len(sub_pts) > 1:
                        C = np.cov(sub_pts, rowvar=False)
                        # Symmetrise + SPD regularisation
                        C = 0.5 * (C + C.T) + 1e-6 * np.eye(D)
                        covars_[k, m] = C
                    else:
                        covars_[k, m] = np.eye(D)
                elif cov_type == "spherical":
                    if len(sub_pts) > 1:
                        # Mean of per-feature variances -> a single scalar.
                        covars_[k, m] = float(sub_pts.var(axis=0).mean()) + 1e-6
                    else:
                        covars_[k, m] = 1.0
                else:  # "diag"
                    covars_[k, m] = (
                        sub_pts.var(axis=0) + 1e-3 if len(sub_pts) > 1 else 1.0
                    )
        return {"means_": means_, "covars_": covars_, "weights_": weights_}

    if e.type == "multinomial":
        # kmeans on integer values is degenerate. Fall back to global empirical
        # frequencies repeated K times, with a small jitter to break symmetry.
        import warnings

        warnings.warn(
            "kmeans init on Multinomial is degenerate; using global empirical frequencies."
        )
        n_symbols = e.n_symbols
        counts = np.bincount(X.astype(int).ravel(), minlength=n_symbols).astype(float)
        global_freq = counts / counts.sum()
        rng = np.random.default_rng(seed)
        emissionprob_ = np.tile(global_freq, (K, 1))
        emissionprob_ += rng.uniform(0, 0.01, size=emissionprob_.shape)
        emissionprob_ /= emissionprob_.sum(axis=1, keepdims=True)
        return {"emissionprob_": emissionprob_}

    if e.type == "poisson":
        km = KMeans(n_clusters=K, random_state=seed, n_init=10).fit(X)
        # hmmlearn PoissonHMM expects `lambdas_` shape (K, D), so use cluster
        # means in the original (positive) units.
        lambdas_ = np.clip(km.cluster_centers_, 1e-6, None)
        return {"lambdas_": lambdas_}

    raise ValueError(f"unknown emission type: {e.type!r}")


def _empirical_covars(
    X: np.ndarray,
    labels: np.ndarray,
    K: int,
    covariance_type: str,
) -> np.ndarray:
    D = X.shape[1]
    if covariance_type == "full":
        out = np.zeros((K, D, D))
        for k in range(K):
            pts = X[labels == k]
            if len(pts) > 1:
                out[k] = np.cov(pts, rowvar=False) + 1e-3 * np.eye(D)
            else:
                out[k] = np.eye(D)
        return out
    if covariance_type == "diag":
        out = np.zeros((K, D))
        for k in range(K):
            pts = X[labels == k]
            out[k] = pts.var(axis=0) + 1e-3 if len(pts) > 1 else np.ones(D)
        return out
    if covariance_type == "spherical":
        out = np.zeros(K)
        for k in range(K):
            pts = X[labels == k]
            out[k] = pts.var() + 1e-3 if len(pts) > 1 else 1.0
        return out
    if covariance_type == "tied":
        return np.cov(X, rowvar=False) + 1e-3 * np.eye(D)
    raise ValueError(f"unknown covariance_type: {covariance_type!r}")
