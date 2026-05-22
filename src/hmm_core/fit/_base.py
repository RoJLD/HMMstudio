"""Shared utilities for constrained HMM fits."""

from __future__ import annotations

import warnings

import numpy as np


def _apply_mask(transmat: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Multiply ``transmat`` by binary ``mask`` and renormalize rows to sum to 1.

    Guarantees:
      * ``out[i, j] == 0`` wherever ``mask[i, j]`` is False.
      * ``out.sum(axis=1) ≈ 1`` on every row (atol 1e-12).
      * If a row's masked product is entirely zero (e.g. all probability mass
        was on now-forbidden edges), fall back to uniform over allowed edges
        in that row and emit a UserWarning.

    Raises
    ------
    ValueError
        If a row of ``mask`` has zero True entries (no allowed edges), or if
        ``transmat`` and ``mask`` have mismatched shapes.
    """
    if transmat.shape != mask.shape:
        raise ValueError(f"shape mismatch: transmat {transmat.shape}, mask {mask.shape}")

    allowed_per_row = mask.sum(axis=1)
    if (allowed_per_row == 0).any():
        bad = np.where(allowed_per_row == 0)[0]
        raise ValueError(f"empty mask row(s) at index {bad.tolist()} — no allowed edges")

    masked = transmat * mask
    row_sums = masked.sum(axis=1, keepdims=True)

    zero_rows = row_sums.squeeze(axis=1) == 0
    if zero_rows.any():
        bad = np.where(zero_rows)[0]
        warnings.warn(
            f"transmat row(s) {bad.tolist()} entirely zero after masking — "
            "falling back to uniform over allowed edges",
            stacklevel=2,
        )

    # Fallback: rows where masked is entirely zero (e.g. probability moved to
    # forbidden edges only). Distribute uniformly over allowed edges.
    fallback = mask.astype(float) / allowed_per_row[:, None]
    safe_sums = np.where(row_sums > 0, row_sums, 1.0)
    normalized = masked / safe_sums
    out = np.where(row_sums > 0, normalized, fallback)
    return out


def _map_update(
    transmat: np.ndarray,
    prior: np.ndarray | None,
    mask: np.ndarray,
    effective_n: float = 1.0,
) -> np.ndarray:
    """Apply Dirichlet MAP smoothing.

    Posterior ∝ likelihood * prior. For Dirichlet(prior) + multinomial
    likelihood, MAP = (counts + prior - 1) / sum(...). hmmlearn's
    ``_do_mstep`` gives us the row-normalized transmat (post-likelihood); we
    blend in the prior as pseudo-counts scaled by ``effective_n``.

    The choice ``Dirichlet(1)`` = uniform = no effect (pseudo-counts all 0).

    Parameters
    ----------
    transmat
        ``(K, K)`` row-normalized transition matrix from the EM M-step.
    prior
        ``(K, K)`` Dirichlet pseudo-count matrix, or None (no-op).
    mask
        ``(K, K)`` boolean mask of allowed transitions.
    effective_n
        Weight given to the observed transition probabilities relative to the
        prior. Default 1.0 — the prior counts as one effective observation
        per row.

    Returns
    -------
    np.ndarray
        MAP-smoothed, mask-re-applied, row-normalized ``(K, K)`` transmat.
    """
    if prior is None:
        return transmat
    pseudo = np.maximum(prior - 1.0, 0.0)
    numerator = transmat * effective_n + pseudo
    numerator = numerator * mask
    row_sums = numerator.sum(axis=1, keepdims=True)
    safe_sums = np.where(row_sums > 0, row_sums, 1.0)
    out = np.where(row_sums > 0, numerator / safe_sums, transmat)
    return out
