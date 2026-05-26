"""Non-homogeneous HMM: covariate-dependent transitions on top of a base fit.

Two-stage algorithm (lighter than full joint EM):
  1. Fit a regular HMM (any emission) via ``hmm_core.fit.fit`` -> get Viterbi.
  2. For each source state ``i``, fit a multinomial logistic regression of the
     observed next-state on the covariates ``Z[t]``. This gives time-varying
     transition rows ``A_ij(t) = P(next=j | current=i, Z[t])``.

The mask from the base ``Topology`` is enforced on every row of every ``A_t``
slice. Source states with fewer than ``min_transitions`` observed transitions
fall back to the homogeneous base transmat row.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from hmm_core.fit import FittedModel, fit
from hmm_core.fit._base import _apply_mask
from hmm_core.topology import Topology


@dataclass(frozen=True)
class NHMMFittedModel:
    """Wraps a base FittedModel with a time-varying transition matrix A_t."""

    base: FittedModel
    covariate_names: list[str]
    A_t: np.ndarray  # (T, K, K), each row already mask-respected & normalized
    classifiers: dict[int, object]  # source_state -> LogisticRegression
    fallback_rows: dict[
        int, np.ndarray
    ]  # source_state -> homogeneous row (K,) for states without classifiers

    @property
    def n_states(self) -> int:
        return self.base.topology.n_states

    @property
    def topology(self) -> Topology:
        return self.base.topology

    def A_at(self, t_idx: int) -> np.ndarray:
        """Return the K x K transition matrix at time index t_idx.

        Out-of-range indices fall back to the base (homogeneous) transmat.
        """
        if 0 <= t_idx < len(self.A_t):
            return self.A_t[t_idx]
        return self.base.model.transmat_

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter (Phase I.1)."""
        from hmm_core._jupyter import (
            render_chip_list,
            render_matrix_heatmap,
            render_stats_table,
            wrap_html,
        )

        K = self.n_states
        T = self.A_t.shape[0]
        mask = self.topology.transition_mask()

        n_classifiers = len(self.classifiers)
        n_fallback = len(self.fallback_rows)

        stats_rows = [
            ("Base topology", self.topology.name),
            ("States (K)", K),
            ("Sequence length (T)", T),
            ("Covariates", render_chip_list(self.covariate_names)),
            ("Logit classifiers fitted", f"{n_classifiers} / {K} source states"),
            ("Fallback rows", f"{n_fallback} (homogeneous fallback)"),
            ("Base log-likelihood", f"{self.base.log_likelihood:.3f}"),
            ("Base BIC", f"{self.base.bic:.3f}"),
        ]
        stats_html = render_stats_table(stats_rows)

        # Mean A_t over t (gives a static homogeneous-equivalent view)
        A_mean = self.A_t.mean(axis=0)
        heatmap_mean = render_matrix_heatmap(
            A_mean,
            self.topology.state_names,
            self.topology.state_names,
            forbidden_mask=mask,
            title="A_t averaged over T (homogeneous-equivalent view)",
        )

        # Variability heatmap : std of A_t across t (shows where covariates matter)
        A_std = self.A_t.std(axis=0)
        heatmap_std = render_matrix_heatmap(
            A_std,
            self.topology.state_names,
            self.topology.state_names,
            forbidden_mask=mask,
            title="A_t variability across t (std)",
        )

        return wrap_html(
            "<h4>NHMMFittedModel</h4>",
            stats_html,
            heatmap_mean,
            heatmap_std,
            '<div class="small">Use <code>.A_at(t)</code> for the transition '
            "matrix at a specific time, or <code>.A_t</code> for the full "
            "(T, K, K) array.</div>",
        )


def fit_nhmm(
    topology: Topology,
    X: np.ndarray,
    Z: np.ndarray,
    *,
    covariate_names: list[str],
    seed: int | None = None,
    lengths: np.ndarray | None = None,
    min_transitions: int = 10,
    regularization: float = 1.0,
) -> NHMMFittedModel:
    """Fit a 2-stage NHMM.

    Parameters
    ----------
    topology : Topology
        Base topology (any emission). Same as for the homogeneous ``fit()``.
    X : ndarray, shape (T, n_features)
        Observations.
    Z : ndarray, shape (T, n_covariates)
        Covariates that drive transitions.
    covariate_names : list[str]
        Names of the columns in Z (for metadata/inspection).
    seed : int, optional
        Overrides ``topology.init.seed`` for the base fit.
    lengths : ndarray, optional
        Sequence lengths for multi-sequence X (matches hmm_core.fit.fit).
    min_transitions : int, default=10
        Minimum (Z[t], next_state) observations required to fit a logistic
        regression for a source state. Below this, the source state's A_t
        row is the homogeneous transmat row from the base fit.
    regularization : float, default=1.0
        Inverse regularization strength ``C`` for the logistic regression.

    Returns
    -------
    NHMMFittedModel
    """
    if Z.shape[0] != X.shape[0]:
        raise ValueError(
            f"X and Z must have the same number of rows; got X={X.shape[0]}, Z={Z.shape[0]}"
        )
    if Z.shape[1] != len(covariate_names):
        raise ValueError(
            f"Z has {Z.shape[1]} columns but covariate_names has {len(covariate_names)}"
        )

    base = fit(topology, X, seed=seed, lengths=lengths)
    K = base.topology.n_states
    viterbi = base.model.predict(X)
    mask = base.topology.transition_mask()

    # Collect per-source-state (z, next_state) pairs.
    pairs_t_per_source: dict[int, list[int]] = {i: [] for i in range(K)}
    boundary_idx = _sequence_boundaries(lengths, len(X))
    for t in range(len(viterbi) - 1):
        if t in boundary_idx:
            continue  # don't count cross-sequence transitions
        i = int(viterbi[t])
        pairs_t_per_source[i].append(t)

    classifiers: dict[int, object] = {}
    fallback_rows: dict[int, np.ndarray] = {}

    for i in range(K):
        ts = pairs_t_per_source[i]
        if len(ts) < min_transitions:
            fallback_rows[i] = base.model.transmat_[i]
            continue
        Z_i = Z[ts]
        next_states = viterbi[np.asarray(ts) + 1]
        # Need at least 2 distinct classes for logistic regression.
        unique_targets = np.unique(next_states)
        if len(unique_targets) < 2:
            fallback_rows[i] = base.model.transmat_[i]
            continue
        clf = LogisticRegression(
            C=regularization,
            solver="lbfgs",
            max_iter=200,
            random_state=seed if seed is not None else 0,
        )
        clf.fit(Z_i, next_states)
        classifiers[i] = clf

    # Build A_t: for each t, predict next-state probabilities given Z[t].
    T = len(X)
    A_t = np.zeros((T, K, K))
    for i in range(K):
        if i in classifiers:
            clf = classifiers[i]
            probs = clf.predict_proba(Z)  # (T, n_classes_seen)
            classes = clf.classes_
            row_t = np.zeros((T, K))
            for c_idx, c in enumerate(classes):
                row_t[:, int(c)] = probs[:, c_idx]
            A_t[:, i, :] = row_t
        else:
            # Constant row from base fit, broadcast over time.
            A_t[:, i, :] = fallback_rows[i]

    # Apply mask + renormalize per (t, i) row.
    for t in range(T):
        A_t[t] = _apply_mask(A_t[t], mask)

    return NHMMFittedModel(
        base=base,
        covariate_names=list(covariate_names),
        A_t=A_t,
        classifiers=classifiers,
        fallback_rows=fallback_rows,
    )


def _sequence_boundaries(lengths: np.ndarray | None, total: int) -> set[int]:
    """Return the set of time indices t where (t, t+1) crosses a sequence boundary.

    For lengths=[L1, L2, L3], boundaries are at t = L1-1, L1+L2-1, ... (the
    last timestep of each sequence except the very last).
    """
    if lengths is None:
        return set()
    out: set[int] = set()
    offset = 0
    for L in lengths[:-1]:
        offset += int(L)
        out.add(offset - 1)
    return out
