"""Tests for hmm_core.features — unsupervised feature selection.

Covers the NMI-clustering + medoid selector (spec
``docs/specs/2026-05-27-unsupervised-feature-selection.md`` § 5) :
    - output is a strict subset of the input columns
    - exactly ``n_clusters`` columns survive
    - correlated features collapse to one medoid
    - independent features are all kept when ``n_clusters == p``
    - NMI matrix shape / diagonal / symmetry
    - medoid is the most central member of its cluster
    - validation errors (empty / oversized n_clusters)
    - the prep op wrapper (standalone + inside a Pipeline)
    - reproducibility under a fixed seed

All fixtures use small synthetic DataFrames with a seeded RNG so the tests
are fast and deterministic, with NaN dropped upstream (the k-NN MI estimator
needs clean input).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hmm_core.features import (
    FeatureSelectionResult,
    unsupervised_feature_selection,
)
from hmm_core.prep import OPS, Pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def independent_df():
    """p independent random columns (no shared information)."""
    rng = np.random.default_rng(0)
    n, p = 200, 6
    data = {f"x{i}": rng.normal(0, 1, n) for i in range(p)}
    return pd.DataFrame(data)


@pytest.fixture
def correlated_df():
    """Two near-identical columns (A, B) plus independent columns.

    ``B = A + tiny noise`` so A and B carry essentially the same information
    and must end up in the same NMI cluster.
    """
    rng = np.random.default_rng(1)
    n = 200
    a = rng.normal(0, 1, n)
    df = pd.DataFrame(
        {
            "A": a,
            "B": a + rng.normal(0, 1e-3, n),  # quasi-duplicate of A
            "C": rng.normal(0, 1, n),
            "D": rng.normal(0, 1, n),
            "E": rng.normal(0, 1, n),
        }
    )
    return df


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


def test_selection_returns_subset(independent_df):
    result = unsupervised_feature_selection(independent_df, n_clusters=3)
    assert isinstance(result, FeatureSelectionResult)
    assert set(result.selected.columns).issubset(set(independent_df.columns))
    # row index preserved
    assert result.selected.index.equals(independent_df.index)


def test_n_clusters_equals_n_selected(independent_df):
    result = unsupervised_feature_selection(independent_df, n_clusters=4)
    assert len(result.selected.columns) == 4
    assert len(result.medoid_per_cluster) == 4
    assert len(result.cluster_dict) == 4


def test_correlated_features_collapse(correlated_df):
    """A and B are quasi-identical -> they cluster together, only one medoid
    survives. With n_clusters < n_features, at most one of {A, B} is kept."""
    result = unsupervised_feature_selection(correlated_df, n_clusters=4)
    kept = set(result.selected.columns)
    assert len({"A", "B"} & kept) <= 1
    # A and B must share a cluster
    cluster_of = {
        name: cid
        for cid, names in result.cluster_dict.items()
        for name in names
    }
    assert cluster_of["A"] == cluster_of["B"]


def test_independent_features_all_kept(independent_df):
    """p independent columns with n_clusters=p -> every column kept."""
    p = independent_df.shape[1]
    result = unsupervised_feature_selection(independent_df, n_clusters=p)
    assert set(result.selected.columns) == set(independent_df.columns)


def test_nmi_matrix_shape_and_diag(independent_df):
    p = independent_df.shape[1]
    result = unsupervised_feature_selection(independent_df, n_clusters=3)
    matrix = result.nmi_matrix
    assert matrix.shape == (p, p)
    assert np.allclose(np.diag(matrix), 1.0)
    assert np.allclose(matrix, matrix.T)
    # NMI values are bounded in [0, 1]
    assert matrix.min() >= 0.0
    assert matrix.max() <= 1.0


def test_medoid_is_most_central(correlated_df):
    """Within a multi-member cluster, the returned medoid has the highest
    mean NMI to its cluster-mates."""
    result = unsupervised_feature_selection(correlated_df, n_clusters=4)
    columns = list(correlated_df.columns)
    matrix = result.nmi_matrix

    found_multi = False
    for cid, names in result.cluster_dict.items():
        if len(names) < 2:
            continue
        found_multi = True
        idxs = [columns.index(n) for n in names]
        sub = matrix[np.ix_(idxs, idxs)].copy()
        np.fill_diagonal(sub, 0.0)
        centrality = sub.mean(axis=1)
        expected_medoid = names[int(np.argmax(centrality))]
        assert result.medoid_per_cluster[cid] == expected_medoid
    assert found_multi, "fixture should produce at least one multi-member cluster"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_n_clusters_exceeds_features_raises(independent_df):
    with pytest.raises(ValueError, match="n_clusters"):
        unsupervised_feature_selection(
            independent_df, n_clusters=independent_df.shape[1] + 1
        )


def test_empty_features_raises():
    empty = pd.DataFrame(index=range(50))  # rows but zero columns
    with pytest.raises(ValueError, match="zero columns"):
        unsupervised_feature_selection(empty, n_clusters=2)


# ---------------------------------------------------------------------------
# Prep op wrapper
# ---------------------------------------------------------------------------


def test_prep_op_select_features_unsupervised(correlated_df):
    # standalone op call
    out = OPS["select_features_unsupervised"](correlated_df, n_clusters=3)
    assert isinstance(out, pd.DataFrame)
    assert set(out.columns).issubset(set(correlated_df.columns))
    assert len(out.columns) == 3

    # inside a Pipeline
    pipe = Pipeline().add_step("select_features_unsupervised", n_clusters=3)
    result = pipe.fit_transform(correlated_df)
    assert set(result.df.columns).issubset(set(correlated_df.columns))
    assert len(result.df.columns) == 3
    # A and B are quasi-duplicates -> at most one survives
    assert len({"A", "B"} & set(result.df.columns)) <= 1


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


def test_reproducible_with_seed(correlated_df):
    r1 = unsupervised_feature_selection(correlated_df, n_clusters=3, random_state=7)
    r2 = unsupervised_feature_selection(correlated_df, n_clusters=3, random_state=7)
    assert list(r1.selected.columns) == list(r2.selected.columns)
    assert np.allclose(r1.nmi_matrix, r2.nmi_matrix)


def test_similarity_matrix_alias_equivalence(independent_df):
    """`result.similarity_matrix` and `result.nmi_matrix` must point at the same
    array — `nmi_matrix` is a backward-compat alias."""
    result = unsupervised_feature_selection(independent_df, n_clusters=3)
    assert hasattr(result, "similarity_matrix")
    assert result.similarity_matrix is result.nmi_matrix


# --- dcor criterion ------------------------------------------------------

dcor = pytest.importorskip("dcor")  # whole-module skip if extra not installed


@pytest.mark.parametrize("criterion", ["nmi", "dcor"])
def test_selection_returns_subset_per_criterion(independent_df, criterion):
    result = unsupervised_feature_selection(
        independent_df, n_clusters=3, criterion=criterion
    )
    assert set(result.selected.columns).issubset(set(independent_df.columns))
    assert len(result.selected.columns) == 3


@pytest.mark.parametrize("criterion", ["nmi", "dcor"])
def test_correlated_features_collapse_per_criterion(correlated_df, criterion):
    """A and B are near-duplicates — both criteria must put them in the same
    cluster and keep at most one of them."""
    result = unsupervised_feature_selection(
        correlated_df, n_clusters=4, criterion=criterion
    )
    kept = set(result.selected.columns)
    assert len({"A", "B"} & kept) <= 1
    cluster_of = {
        name: cid
        for cid, names in result.cluster_dict.items()
        for name in names
    }
    assert cluster_of["A"] == cluster_of["B"]


def test_dcor_similarity_matrix_properties(independent_df):
    """dcor matrix must be symmetric, in [0, 1], with 1.0 on the diagonal."""
    p = independent_df.shape[1]
    result = unsupervised_feature_selection(
        independent_df, n_clusters=3, criterion="dcor"
    )
    M = result.similarity_matrix
    assert M.shape == (p, p)
    assert np.allclose(np.diag(M), 1.0)
    assert np.allclose(M, M.T)
    assert M.min() >= 0.0
    assert M.max() <= 1.0


def test_criterion_invalid_value_raises(independent_df):
    with pytest.raises(ValueError, match="criterion"):
        unsupervised_feature_selection(
            independent_df, n_clusters=3, criterion="kendall"
        )


def test_prep_op_passes_criterion(correlated_df):
    """The select_features_unsupervised prep op forwards `criterion` to the
    underlying selector."""
    op = OPS["select_features_unsupervised"]
    out = op(correlated_df, n_clusters=4, criterion="dcor")
    assert out.shape[1] == 4
    kept = set(out.columns)
    assert len({"A", "B"} & kept) <= 1
