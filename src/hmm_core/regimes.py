"""Semantic labelling of fitted HMM states.

After EM, hidden states have arbitrary integer indices — state 0 is not
inherently "the low one". For interpretation you usually want a stable
ordering : sort states by some property of their emission (mean return,
mean count, …) and attach human labels.

This module provides the canonicalisation helpers, kept generic (works on
any ``FittedModel``) rather than tied to one paper's preset. The Giudici
2020 BTC-regime convention (bear / stable / bull, sorted by mean
log-return) is the motivating example — see
``examples/giudici_2020_btc_regimes.yaml``.
"""

from __future__ import annotations

import numpy as np

from hmm_core.fit import FittedModel


def _state_feature_means(fitted: FittedModel, feature: int) -> np.ndarray:
    """Per-state mean of the given observation feature, read off the model.

    Works for Gaussian and GMM emissions (uses ``means_``) and for Poisson
    (uses ``lambdas_``). For Multinomial there is no continuous "mean
    feature", so this raises — ordering categorical states by a numeric
    statistic is not well-defined.
    """
    model = fitted.model
    if hasattr(model, "means_"):
        means = np.asarray(model.means_)
        if means.ndim == 3:  # GMM: (K, n_mix, D) -> weight-average over mixtures
            weights = np.asarray(getattr(model, "weights_", None))
            if weights is not None and weights.shape[:2] == means.shape[:2]:
                # weighted mean over the mixture axis
                state_means = np.einsum("km,kmd->kd", weights, means)
            else:
                state_means = means.mean(axis=1)
        else:  # Gaussian: (K, D)
            state_means = means
        return state_means[:, feature]
    if hasattr(model, "lambdas_"):
        return np.asarray(model.lambdas_)[:, feature]
    raise TypeError(
        "regime ordering by feature mean needs a model with means_ "
        "(Gaussian/GMM) or lambdas_ (Poisson); "
        f"got {type(model).__name__} without either."
    )


def regime_order_by_feature_mean(fitted: FittedModel, feature: int = 0) -> list[int]:
    """Return state indices sorted ascending by their mean of ``feature``.

    ``result[0]`` is the lowest-mean state, ``result[-1]`` the highest. For
    the Giudici BTC convention with ``feature=0`` (log-return), that is
    ``[bear, stable, bull]``.

    Parameters
    ----------
    fitted
        A fitted model (Gaussian / GMM / Poisson emission).
    feature
        Observation-feature index to sort on (default 0).

    Returns
    -------
    list[int]
        Permutation of ``range(n_states)``.
    """
    means = _state_feature_means(fitted, feature)
    return [int(i) for i in np.argsort(means)]


def regime_labels(
    fitted: FittedModel,
    labels: list[str],
    feature: int = 0,
) -> dict[int, str]:
    """Map each raw state index to a human label, ordered by mean of ``feature``.

    The lowest-mean state gets ``labels[0]``, the highest ``labels[-1]``.

    Example (Giudici 2020) ::

        labels = regime_labels(result, ["bear", "stable", "bull"])
        # -> {2: "bear", 0: "stable", 1: "bull"}  (raw idx -> label)

    Parameters
    ----------
    fitted
        A fitted model.
    labels
        One label per state, in ascending-mean order. ``len(labels)`` must
        equal ``fitted.topology.n_states``.
    feature
        Observation-feature index to sort on (default 0).

    Raises
    ------
    ValueError
        If ``len(labels)`` does not match the number of states.
    """
    k = fitted.topology.n_states
    if len(labels) != k:
        raise ValueError(f"expected {k} labels (one per state), got {len(labels)}")
    order = regime_order_by_feature_mean(fitted, feature)
    return {raw_idx: labels[rank] for rank, raw_idx in enumerate(order)}
