"""Initialization strategies for constrained HMM fits.

All ``transmat`` strategies respect ``topology.transition_mask()`` by construction;
a final ``_apply_mask`` is used as a safety net.
"""

from __future__ import annotations

import numpy as np

from hmm_core.fit._base import _apply_mask
from hmm_core.topology import Topology


def transmat(topology: Topology, *, seed: int, X: np.ndarray | None = None) -> np.ndarray:
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
        for t in range(len(labels) - 1):
            counts[labels[t], labels[t + 1]] += 1
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
    topology: Topology, X: np.ndarray | None, *, seed: int,
) -> dict[str, np.ndarray]:
    """Return dict of pre-set emission parameters.

    For Gaussian/GMM: ``means_`` and ``covars_``.
    For Multinomial: ``emissionprob_``.
    For Poisson: ``lambdas_``.

    Empty dict if the strategy does not pre-set emissions (uniform, random).
    """
    strategy = topology.init.strategy
    if strategy in ("uniform", "random"):
        return {}

    if strategy == "kmeans":
        if X is None:
            raise ValueError("kmeans emission init requires X")
        return _kmeans_emission_params(topology, X, seed=seed)

    if strategy == "data_frequencies":
        if X is None:
            raise ValueError("data_frequencies emission init requires X")
        # data_frequencies reuses the kmeans-based emission init.
        return _kmeans_emission_params(topology, X, seed=seed)

    raise ValueError(f"unknown init strategy: {strategy!r}")


def _kmeans_emission_params(
    topology: Topology, X: np.ndarray, *, seed: int,
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
        # For GMM init: per state, fit k=n_mix sub-kmeans (means + diag covars).
        # Returns means_ (K, n_mix, D), covars_ (K, n_mix, D), weights_ (K, n_mix).
        km = KMeans(n_clusters=K, random_state=seed, n_init=10).fit(X)
        D = X.shape[1]
        means_ = np.zeros((K, e.n_mix, D))
        covars_ = np.zeros((K, e.n_mix, D))
        weights_ = np.ones((K, e.n_mix)) / e.n_mix
        for k in range(K):
            cluster_X = X[km.labels_ == k]
            if len(cluster_X) < e.n_mix:
                means_[k] = km.cluster_centers_[k]
                covars_[k] = 1.0
            else:
                sub = KMeans(n_clusters=e.n_mix, random_state=seed, n_init=5).fit(cluster_X)
                means_[k] = sub.cluster_centers_
                for m in range(e.n_mix):
                    pts = cluster_X[sub.labels_ == m]
                    covars_[k, m] = pts.var(axis=0) + 1e-3 if len(pts) > 1 else 1.0
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
    X: np.ndarray, labels: np.ndarray, K: int, covariance_type: str,
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
