"""Shared utilities for the scientific validation suite.

Used by V.2 (recovery) and V.5/V.6 (cross-checks). Kept minimal — most
test files do their own setup since the canonical examples differ.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment


def match_states_by_means(true_means: np.ndarray, est_means: np.ndarray) -> np.ndarray:
    """Hungarian assignment of estimated states to true states by mean distance.

    HMM identifiability is modulo permutation of states. After fitting, the
    estimated state indices have no canonical ordering with respect to the
    true ones used to generate the data. We use the means as anchors and
    find the optimal one-to-one matching via the Hungarian algorithm.

    Parameters
    ----------
    true_means : (K, D)
    est_means  : (K, D)

    Returns
    -------
    permutation : ndarray (K,)
        ``permutation[i] = j`` means true state ``i`` maps to estimated state
        ``j``. Use ``est_means[permutation]`` to get arrays aligned with true.
    """
    if true_means.shape != est_means.shape:
        raise ValueError(
            f"shape mismatch: true {true_means.shape}, est {est_means.shape}"
        )
    # Cost = pairwise Euclidean distance between (true_i, est_j)
    cost = np.linalg.norm(
        true_means[:, None, :] - est_means[None, :, :],
        axis=-1,
    )
    _, col = linear_sum_assignment(cost)
    return col


def match_states_by_emission_prob(
    true_prob: np.ndarray, est_prob: np.ndarray
) -> np.ndarray:
    """Same as ``match_states_by_means`` but for multinomial emissions.

    Cost = total variation distance between distributions.
    """
    if true_prob.shape != est_prob.shape:
        raise ValueError(
            f"shape mismatch: true {true_prob.shape}, est {est_prob.shape}"
        )
    cost = 0.5 * np.abs(true_prob[:, None, :] - est_prob[None, :, :]).sum(axis=-1)
    _, col = linear_sum_assignment(cost)
    return col


def kl_divergence_categorical(p: np.ndarray, q: np.ndarray, eps: float = 1e-12) -> float:
    """KL(p || q) for discrete distributions. ``eps`` prevents log(0)."""
    p = np.asarray(p, dtype=float) + eps
    q = np.asarray(q, dtype=float) + eps
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * (np.log(p) - np.log(q))))


def kl_divergence_transmat(A_true: np.ndarray, A_est: np.ndarray) -> float:
    """Mean per-row KL divergence between two transition matrices.

    Useful as a one-number recovery metric : 0 = identical, > 0.1 typically
    indicates a meaningful divergence on 3-state ergodic problems.
    """
    K = A_true.shape[0]
    return float(np.mean([kl_divergence_categorical(A_true[i], A_est[i]) for i in range(K)]))
