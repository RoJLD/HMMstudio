"""Shared utilities for constrained HMM fits."""

from __future__ import annotations

import numpy as np


def _apply_mask(transmat: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Multiply ``transmat`` by binary ``mask`` and renormalize rows to sum to 1.

    Guarantees:
      * ``out[i, j] == 0`` wherever ``mask[i, j]`` is False.
      * ``out.sum(axis=1) ≈ 1`` on every row (atol 1e-12).
      * If a row's masked product is entirely zero (e.g. all probability mass
        was on now-forbidden edges), fall back to uniform over allowed edges
        in that row.

    Raises
    ------
    ValueError
        If a row of ``mask`` has zero True entries (no allowed edges).
    """
    if transmat.shape != mask.shape:
        raise ValueError(
            f"shape mismatch: transmat {transmat.shape}, mask {mask.shape}"
        )

    allowed_per_row = mask.sum(axis=1)
    if (allowed_per_row == 0).any():
        bad = np.where(allowed_per_row == 0)[0]
        raise ValueError(f"empty mask row(s) at index {bad.tolist()} — no allowed edges")

    masked = transmat * mask
    row_sums = masked.sum(axis=1, keepdims=True)

    # Fallback: rows where masked is entirely zero (e.g. probability moved to
    # forbidden edges only). Distribute uniformly over allowed edges.
    fallback = mask.astype(float) / allowed_per_row[:, None]
    safe_sums = np.where(row_sums > 0, row_sums, 1.0)
    normalized = masked / safe_sums
    out = np.where(row_sums > 0, normalized, fallback)
    return out
