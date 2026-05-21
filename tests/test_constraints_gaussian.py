"""Tests for ConstrainedGaussianHMM: masking, normalization, vanilla equivalence."""

from __future__ import annotations

import numpy as np

from hmm_core.fit.gaussian import ConstrainedGaussianHMM


def test_mask_zeros_preserved_after_fit(synthetic_gaussian_left_right):
    X = synthetic_gaussian_left_right["X"]
    mask = np.array([[True, True, False], [False, True, True], [False, False, True]])
    model = ConstrainedGaussianHMM(
        n_components=3,
        covariance_type="full",
        n_iter=20,
        random_state=42,
        transmat_mask=mask,
    )
    # Pre-set transmat respecting the mask so init does not violate it.
    initial_A = np.array([[0.7, 0.3, 0.0], [0.0, 0.6, 0.4], [0.0, 0.0, 1.0]])
    model.startprob_ = np.array([1.0, 0.0, 0.0])
    model.transmat_ = initial_A
    # init_params: omit 's' and 't' since we pre-set them.
    model.init_params = "mc"
    model.fit(X)

    violation = (model.transmat_ * (~mask)).sum()
    assert violation < 1e-10, f"mask violation: {violation}"


def test_rows_sum_to_one_after_fit(synthetic_gaussian_left_right):
    X = synthetic_gaussian_left_right["X"]
    mask = np.array([[True, True, False], [False, True, True], [False, False, True]])
    model = ConstrainedGaussianHMM(
        n_components=3,
        covariance_type="full",
        n_iter=20,
        random_state=42,
        transmat_mask=mask,
    )
    model.startprob_ = np.array([1.0, 0.0, 0.0])
    model.transmat_ = np.array([[0.7, 0.3, 0.0], [0.0, 0.6, 0.4], [0.0, 0.0, 1.0]])
    model.init_params = "mc"
    model.fit(X)
    np.testing.assert_allclose(model.transmat_.sum(axis=1), 1.0, atol=1e-10)


def test_mask_none_matches_vanilla(synthetic_gaussian_left_right):
    """With mask=None, behavior must match hmmlearn.GaussianHMM exactly."""
    from hmmlearn.hmm import GaussianHMM

    X = synthetic_gaussian_left_right["X"]

    vanilla = GaussianHMM(n_components=3, covariance_type="full", n_iter=20, random_state=42)
    vanilla.fit(X)

    constrained = ConstrainedGaussianHMM(
        n_components=3,
        covariance_type="full",
        n_iter=20,
        random_state=42,
        transmat_mask=None,
    )
    constrained.fit(X)

    np.testing.assert_allclose(constrained.transmat_, vanilla.transmat_, atol=1e-10)
    np.testing.assert_allclose(constrained.means_, vanilla.means_, atol=1e-10)
