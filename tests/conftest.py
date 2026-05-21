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
