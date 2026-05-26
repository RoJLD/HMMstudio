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


def _apply_label_clamp(log_prob: np.ndarray, label_clamp: np.ndarray) -> np.ndarray:
    """Force ``log_prob[t, k] = -inf`` at every labelled position where ``k != label``.

    Used by the semi-supervised EM path (Phase A.7.1): when a Constrained*HMM
    is given a ``_label_clamp`` attribute, its overridden
    ``_compute_log_likelihood`` injects -inf at the forbidden states at
    labelled positions. Forward-backward then naturally produces
    ``alpha[t, k] = 0`` for every wrong state at a labelled position, giving
    an argmax-style E-step there while leaving unlabelled positions free.

    Parameters
    ----------
    log_prob
        ``(T_sub, K)`` float array of emission log-likelihoods for the
        current sub-sequence. Modified in place AND returned (caller-friendly).
    label_clamp
        ``(T_sub,)`` int array. ``-1`` at unlabelled positions; ``k in [0, K)``
        at labelled positions. Must match ``log_prob.shape[0]`` exactly; the
        caller (the ``_compute_log_likelihood`` override on each
        ``Constrained*HMM``) is responsible for slicing the full-length clamp
        by sub-sequence boundaries before passing it in.

    Returns
    -------
    np.ndarray
        The same ``log_prob`` array (mutated) for chaining convenience.
    """
    if label_clamp.shape[0] != log_prob.shape[0]:
        raise ValueError(
            f"label_clamp length {label_clamp.shape[0]} does not match "
            f"log_prob length {log_prob.shape[0]}"
        )
    labelled = label_clamp >= 0
    if not labelled.any():
        return log_prob
    K = log_prob.shape[1]
    idx_t = np.where(labelled)[0]
    labels = label_clamp[idx_t]
    for i, t in enumerate(idx_t):
        true_k = int(labels[i])
        for k in range(K):
            if k != true_k:
                log_prob[t, k] = -np.inf
    return log_prob


def _resolve_clamp_slice(
    full_clamp: np.ndarray,
    segments: list[np.ndarray] | None,
    cursor: list[int],
    T_sub: int,
) -> np.ndarray:
    """Pop the next per-sequence clamp slice, falling back to a length-match.

    The clamp may have been pre-split into one slice per sub-sequence
    (``segments``). We advance ``cursor[0]`` to consume them in order.
    If no segments were provided (single-sequence path), we return the
    full clamp when its length matches ``T_sub`` — otherwise raise, to
    catch silent misuse from downstream calls (e.g. ``.score()`` while
    the clamp is still attached).
    """
    if segments is not None:
        if not segments:
            raise RuntimeError(
                "label_clamp segments exhausted; an extra call to "
                "_compute_log_likelihood was made beyond the EM E-step."
            )
        # Pop the cursor-th segment. Wrap around at the end of each EM
        # iteration via the _estep_begin reset on the model.
        i = cursor[0]
        if i >= len(segments):
            raise RuntimeError(
                "label_clamp cursor exceeds segment count; missed an "
                "_estep_begin reset between EM iterations."
            )
        seg = segments[i]
        if seg.shape[0] != T_sub:
            raise RuntimeError(
                f"label_clamp segment {i} has length {seg.shape[0]} but "
                f"sub-sequence has length {T_sub} — lengths mismatch."
            )
        cursor[0] = i + 1
        return seg
    # Single-sequence path: the full clamp must match T_sub exactly.
    if full_clamp.shape[0] != T_sub:
        raise RuntimeError(
            f"label_clamp length {full_clamp.shape[0]} does not match "
            f"sub-sequence length {T_sub}; pass lengths= and pre-split "
            f"segments for multi-sequence semi-supervised fits."
        )
    return full_clamp


def _smooth_startprob_(model, eps: float = 1e-30) -> None:
    """Smooth ``model.startprob_`` in place ; replace with uniform if NaN/Inf appears.

    Addresses Fix #6: with a strict left-right topology + ``startprob='first_state'``
    (or even ``'uniform'``), hmmlearn's M-step re-fits startprob from the
    forward-backward responsibilities. For states never revisited (state 0 in a
    left-right topology), the per-state responsibility sum collapses to ~0 over
    the sequence and the normalisation produces 0/0 = NaN.

    This helper:

      * skips entirely when startprob is frozen (Fix #7: ``model.params`` does
        not contain ``'s'``), so a hand-crafted prior is preserved exactly;
      * if the array contains any non-finite value, replaces it with the uniform
        distribution (safe fallback);
      * otherwise adds ``eps`` and renormalises so subsequent EM iterations have
        a well-defined startprob_ row.

    ``eps`` is small enough (1e-30) that fits that don't hit the pathology are
    unaffected within the V.1 cross-check tolerance (parameter agreement at
    1e-12 with vanilla hmmlearn) while still being large enough to break the
    0/0 cascade on the next M-step iteration.
    """
    # When startprob is frozen ('s' removed from `params`), don't touch it ;
    # the user is preserving a hand-crafted initial distribution and even an
    # eps shift would be a behaviour change.
    params = getattr(model, "params", None)
    if params is not None and "s" not in params:
        return
    sp = np.asarray(model.startprob_, dtype=float)
    if not np.isfinite(sp).all():
        K = len(sp)
        model.startprob_ = np.full(K, 1.0 / K)
        return
    sp = sp + eps
    model.startprob_ = sp / sp.sum()


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
