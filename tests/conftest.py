"""Shared pytest fixtures for hmm-core tests."""

from __future__ import annotations

import numpy as np
import pytest


def _generate_gaussian_sequence(
    transmat: np.ndarray, means: np.ndarray, covars: np.ndarray, n: int, seed: int,
) -> np.ndarray:
    """Sample n observations from a Gaussian HMM with the given parameters."""
    rng = np.random.default_rng(seed)
    K, D = means.shape
    state = 0
    X = np.zeros((n, D))
    for t in range(n):
        X[t] = rng.multivariate_normal(means[state], covars[state])
        state = int(rng.choice(K, p=transmat[state]))
    return X


@pytest.fixture
def synthetic_gaussian_left_right():
    """K=3 left-right Gaussian HMM, D=2, N=1000, fixed seed."""
    A = np.array([[0.85, 0.15, 0.00],
                  [0.00, 0.80, 0.20],
                  [0.00, 0.00, 1.00]])
    means = np.array([[-2.0, -2.0],
                      [ 0.0,  0.0],
                      [ 3.0,  3.0]])
    covars = np.stack([0.3 * np.eye(2)] * 3)
    X = _generate_gaussian_sequence(A, means, covars, n=1000, seed=42)
    return {"X": X, "A": A, "means": means, "covars": covars}


@pytest.fixture
def synthetic_gmm_3state():
    """K=3 GMM HMM with n_mix=2, D=2, N=800, fixed seed."""
    A = np.array([[0.80, 0.15, 0.05],
                  [0.10, 0.80, 0.10],
                  [0.05, 0.15, 0.80]])
    rng = np.random.default_rng(7)
    # Per state, 2 mixture means
    means = np.array([
        [[-3.0, -3.0], [-2.0, -4.0]],
        [[ 0.0,  0.0], [ 1.0,  1.0]],
        [[ 3.0,  3.0], [ 4.0,  2.0]],
    ])
    state = 0
    n = 800
    X = np.zeros((n, 2))
    for t in range(n):
        m_idx = rng.integers(0, 2)
        X[t] = rng.multivariate_normal(means[state, m_idx], 0.4 * np.eye(2))
        state = int(rng.choice(3, p=A[state]))
    return {"X": X, "A": A}
