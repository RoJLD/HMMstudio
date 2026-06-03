"""Unsupervised feature selection for HMM inputs via NMI clustering.

The prep layer (``hmm_core.prep``) cleans and transforms columns, but it does
not answer the question that comes right before ``fit()`` : *which* features
should the HMM see ? Candidate panels (e.g. 30-40 on-chain crypto indicators)
are typically riddled with correlated, redundant columns — feeding them all to
the emission inflates dimension without adding information.

This module ports the unsupervised selector from the Robin crypto research
(``cmex_crypto/features/unsupervised_selection.py``) : cluster the candidate
features by normalised mutual information (NMI), then keep one representative
(the *medoid*) per cluster. The output is a strict subset of the input
columns, decorrelated and ready to feed ``fit()``.

Algorithm overview
------------------
1. Standardise (``StandardScaler``) + add tiny Gaussian jitter — the
   sklearn k-NN MI estimator cannot handle exact ties.
2. Per-feature entropy proxy ``H(x_i)`` via diagonal MI ``MI(x_i, x_i + jitter)``
   with the same estimator — used as the NMI normaliser.
3. Pairwise ``NMI(x_i, x_j) = MI(x_i, x_j) / sqrt(H_i · H_j)``, clipped to
   ``[0, 1]``.
4. Distance ``D = 1 - NMI`` (symmetrised, zero diagonal).
5. Agglomerative hierarchical clustering (scipy), dendrogram cut at
   ``n_clusters``.
6. Medoid per cluster = the feature with highest mean NMI to its cluster-mates.

The MI / entropy estimation uses the k-nearest-neighbour estimator of
Kraskov, Stögbauer & Grassberger (2004), "Estimating mutual information",
Phys. Rev. E 69, 066138 — the estimator that backs
``sklearn.feature_selection.mutual_info_regression``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class FeatureSelectionResult:
    """Rich output of :func:`unsupervised_feature_selection`.

    Attributes
    ----------
    selected
        ``features[medoids]`` — the selected subset, input row index preserved.
        One column per cluster.
    similarity_matrix
        The full ``(p, p)`` matrix of feature-pair similarity in ``[0, 1]``,
        symmetric with ``1.0`` on the diagonal. Contains NMI when the selector
        ran with ``criterion="nmi"`` (the default), or dcor values when
        ``criterion="dcor"``. Useful for a diagnostic heatmap.
    cluster_dict
        Mapping ``cluster_id -> list of feature names`` in that cluster.
    medoid_per_cluster
        Mapping ``cluster_id -> medoid feature name`` (the retained column).
    """

    selected: pd.DataFrame
    similarity_matrix: np.ndarray
    cluster_dict: dict[int, list[str]]
    medoid_per_cluster: dict[int, str]

    @property
    def nmi_matrix(self) -> np.ndarray:
        """Legacy alias for :attr:`similarity_matrix` (kept for backward compat)."""
        return self.similarity_matrix


def _entropy_diagonal(standardized: np.ndarray, n_neighbors: int, seed: int) -> np.ndarray:
    """Per-variable entropy proxy ``H(x_i)`` via diagonal MI.

    Estimates ``MI(x_i, x_i + jitter)`` with the same k-NN estimator as
    :func:`sklearn.feature_selection.mutual_info_regression` (Kraskov et al.
    2004). This serves as the normaliser of
    ``NMI(x_i, x_j) = MI(x_i, x_j) / sqrt(H(x_i) H(x_j))``.

    A tiny jitter (magnitude ``1e-10``, below feature noise but above machine
    epsilon) keeps the estimator numerically stable on perfectly
    self-correlated data.
    """
    n_vars = standardized.shape[1]
    entropy = np.zeros(n_vars)
    rng = np.random.default_rng(seed)
    for i in range(n_vars):
        xi = standardized[:, i].reshape(-1, 1)
        jitter = rng.normal(0.0, 1e-10, size=xi.shape)
        entropy[i] = mutual_info_regression(
            xi, (xi + jitter).ravel(), n_neighbors=n_neighbors, random_state=seed
        )[0]
    return entropy


_DCOR_EXTRA_HINT = (
    "criterion='dcor' requires the 'dcor' extra: "
    "pip install \"hmm-studio[dcor]\""
)


def _dcor_matrix(standardized: np.ndarray) -> np.ndarray:
    """Distance-correlation similarity matrix.

    Returns a symmetric ``(p, p)`` matrix with values in ``[0, 1]`` and ``1.0``
    on the diagonal. Uses the ``dcor`` package (Székely, Rizzo & Bakirov 2007).
    """
    try:
        import dcor
    except ImportError as exc:
        raise ImportError(_DCOR_EXTRA_HINT) from exc

    p = standardized.shape[1]
    M = np.zeros((p, p))
    for i in range(p):
        M[i, i] = 1.0
        for j in range(i + 1, p):
            d = float(dcor.distance_correlation(
                standardized[:, i], standardized[:, j]
            ))
            M[i, j] = d
            M[j, i] = d
    return M


def _cluster_and_pick_medoids(
    similarity_matrix: np.ndarray,
    columns: list[str],
    n_clusters: int,
    linkage_method: str,
) -> tuple[dict[int, str], dict[int, list[str]], list[str]]:
    """Cluster + medoid pipeline shared by every criterion.

    Parameters
    ----------
    similarity_matrix
        Symmetric ``(p, p)`` matrix with values in ``[0, 1]`` and ``1.0`` on the
        diagonal (higher = more redundant).
    columns
        Feature names, length ``p``, in the same order as the matrix.
    n_clusters
        Number of clusters to cut the dendrogram at.
    linkage_method
        scipy.cluster.hierarchy linkage method (``"average"`` is the documented
        default for NMI-style 1-similarity distances).

    Returns
    -------
    medoid_per_cluster : dict[int, str]
    cluster_dict       : dict[int, list[str]]
    selected_names     : list[str]  (one medoid per cluster, sorted by cluster id)
    """
    distance = 1.0 - similarity_matrix
    np.fill_diagonal(distance, 0.0)
    distance = 0.5 * (distance + distance.T)
    linkage = hierarchy.linkage(
        squareform(distance, checks=False), method=linkage_method
    )
    cluster_ids = hierarchy.fcluster(linkage, n_clusters, criterion="maxclust")

    clusters: dict[int, list[str]] = defaultdict(list)
    for name, cid in zip(columns, cluster_ids, strict=False):
        clusters[int(cid)].append(name)

    medoids: dict[int, str] = {}
    selected_names: list[str] = []
    for cid, cols in sorted(clusters.items()):
        if len(cols) == 1:
            medoid = cols[0]
        else:
            idxs = [columns.index(c) for c in cols]
            sub = similarity_matrix[np.ix_(idxs, idxs)].copy()
            np.fill_diagonal(sub, 0.0)
            centrality = sub.mean(axis=1)
            medoid = cols[int(np.argmax(centrality))]
        medoids[cid] = medoid
        selected_names.append(medoid)

    return medoids, dict(clusters), selected_names


def unsupervised_feature_selection(
    features: pd.DataFrame,
    n_clusters: int = 10,
    *,
    criterion: str = "nmi",
    n_neighbors: int = 5,
    linkage_method: str = "average",
    jitter_std: float = 1e-8,
    random_state: int = 42,
) -> FeatureSelectionResult:
    """Select one medoid feature per NMI-cluster from ``features``.

    Cluster the candidate features by normalised mutual information and keep
    one representative per cluster, yielding a decorrelated subset of the
    input columns ready to feed an HMM ``fit()``.

    Algorithm
    ---------
    1. Standardise + add tiny Gaussian jitter (the sklearn k-NN MI estimator
       cannot handle exact ties).
    2. Estimate per-feature entropy ``H(x_i)`` via diagonal MI with
       self+jitter.
    3. Estimate pairwise ``NMI(x_i, x_j) = MI(x_i, x_j) / sqrt(H_i H_j)`` and
       clip into ``[0, 1]``.
    4. Build distance ``D = 1 - NMI`` (symmetrised, zero diagonal) and run
       agglomerative hierarchical clustering with ``linkage_method``.
    5. Cut the dendrogram at ``n_clusters`` clusters. Within each cluster the
       medoid = the feature with highest mean NMI to its cluster-mates.

    The MI/entropy estimator is the k-NN estimator of Kraskov, Stögbauer &
    Grassberger (2004), "Estimating mutual information", Phys. Rev. E 69,
    066138 — the same estimator backing
    :func:`sklearn.feature_selection.mutual_info_regression`.

    Parameters
    ----------
    features
        DataFrame with one column per candidate feature. NaN rows must be
        dropped upstream (the k-NN MI estimator silently produces zeros on
        them otherwise).
    n_clusters
        Number of clusters to retain — equals the number of selected
        features. Must be ``<= features.shape[1]``.
    criterion
        Similarity criterion. ``"nmi"`` (default) uses normalised mutual
        information via the sklearn k-NN estimator. ``"dcor"`` uses distance
        correlation (Székely, Rizzo & Bakirov 2007) — deterministic, no
        jitter / k-NN tuning, requires the optional ``dcor`` extra
        (``pip install "hmm-studio[dcor]"``). ``n_neighbors``, ``jitter_std``
        and ``random_state`` are ignored when ``criterion="dcor"``.
    n_neighbors
        ``k`` for the k-NN entropy/MI estimator. sklearn's default is 3 ; we
        use 5 following Kraskov et al. 2004 §III.B, which recommends
        ``k ∈ [3, 10]`` for the bias/variance trade-off on continuous data.
    linkage_method
        scipy.cluster.hierarchy linkage method. ``"average"`` (default) is the
        most stable on NMI distance ; ``"ward"`` requires Euclidean geometry
        and is not valid on a 1-NMI distance matrix.
    jitter_std
        Scale of the regularising noise added to the standardised features
        before MI estimation. Below feature noise, above machine epsilon.
    random_state
        Seed for the jitter RNG and the sklearn MI estimator.

    Returns
    -------
    FeatureSelectionResult
        ``selected`` = ``features[medoids]`` preserving the input row index ;
        ``nmi_matrix`` = the full p×p NMI matrix (with ``NMI(x_i, x_i) = 1``) ;
        ``cluster_dict`` = ``cluster_id -> list of feature names`` ;
        ``medoid_per_cluster`` = ``cluster_id -> medoid feature name``.

    Raises
    ------
    ValueError
        If ``features`` has zero columns, or if ``n_clusters`` exceeds the
        number of features.
    """
    if features.shape[1] == 0:
        raise ValueError("features DataFrame has zero columns")
    if n_clusters > features.shape[1]:
        raise ValueError(f"n_clusters={n_clusters} > number of features ({features.shape[1]})")

    rng = np.random.default_rng(random_state)
    columns = list(features.columns)
    n_vars = len(columns)

    standardized = StandardScaler().fit_transform(features.values).astype(np.float64)
    standardized = standardized + rng.normal(0.0, jitter_std, size=standardized.shape)

    if criterion not in {"nmi", "dcor"}:
        raise ValueError(
            f"criterion must be 'nmi' or 'dcor', got {criterion!r}"
        )

    if criterion == "dcor":
        similarity = _dcor_matrix(standardized)
        medoids, clusters, selected_names = _cluster_and_pick_medoids(
            similarity_matrix=similarity,
            columns=columns,
            n_clusters=n_clusters,
            linkage_method=linkage_method,
        )
        return FeatureSelectionResult(
            selected=features[selected_names],
            similarity_matrix=similarity,
            cluster_dict=clusters,
            medoid_per_cluster=medoids,
        )

    entropy = _entropy_diagonal(
        standardized, n_neighbors=n_neighbors, seed=random_state
    )
    entropy = np.where(entropy < 1e-12, 1e-12, entropy)

    mi_matrix = np.zeros((n_vars, n_vars))
    for i in range(n_vars):
        if i < n_vars - 1:
            scores = mutual_info_regression(
                standardized[:, i + 1 :],
                standardized[:, i],
                n_neighbors=n_neighbors,
                random_state=random_state,
            )
            mi_matrix[i, i + 1 :] = scores
            mi_matrix[i + 1 :, i] = scores
    np.clip(mi_matrix, 0, None, out=mi_matrix)

    nmi_matrix = mi_matrix / np.sqrt(np.outer(entropy, entropy))
    np.clip(nmi_matrix, 0.0, 1.0, out=nmi_matrix)
    np.fill_diagonal(nmi_matrix, 1.0)

    medoids, clusters, selected_names = _cluster_and_pick_medoids(
        similarity_matrix=nmi_matrix,
        columns=columns,
        n_clusters=n_clusters,
        linkage_method=linkage_method,
    )

    return FeatureSelectionResult(
        selected=features[selected_names],
        similarity_matrix=nmi_matrix,
        cluster_dict=clusters,
        medoid_per_cluster=medoids,
    )
