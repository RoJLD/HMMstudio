"""GMM-NHMM (Phase A.10): GMM emissions + covariate-dependent transitions.

Two-stage fit (MVP, "Stratégie A" per docs/decisions/0007):
  1. Fit a regular GMMHMM (homogeneous transitions, GMM emissions) on X.
  2. Per source state i: fit multinomial logistic regression of next-state on
     covariates Z, on the observed (Z[t], z[t+1]) pairs from Viterbi.

The result is a `GMMNHMMFittedModel` with:
  - `base`: the fitted GMMHMM wrapped in our FittedModel
  - `A_t`: (T, K, K) time-varying transition matrix from covariates
  - `classifiers`: per-source-state logistic regression

This is the SAME pattern as `hmm_core.fit_nhmm` (Phase A.1), just with a GMM
base instead of GaussianHMM base. Full joint EM is deferred to A.10.x.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from hmm_core.fit import FittedModel, fit
from hmm_core.fit._base import _apply_mask
from hmm_core.topology import Topology, TopologyError


@dataclass(frozen=True)
class GMMNHMMFittedModel:
    """Wrapper around a GMM base fit + per-state transition classifiers."""

    base: FittedModel
    covariate_names: list[str]
    A_t: np.ndarray  # (T, K, K), mask-respected, row-normalized
    classifiers: dict[int, object]  # source_state -> LogisticRegression
    fallback_rows: dict[int, np.ndarray]  # source -> homogeneous row when too few transitions

    @property
    def n_states(self) -> int:
        return self.base.topology.n_states

    @property
    def n_mix(self) -> int:
        return self.base.topology.emission.n_mix or 1

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

    def to_summary_dict(self) -> dict:
        """Flat dict of GMM-NHMM fit metadata (extends the base FittedModel summary)."""
        d = self.base.to_summary_dict()
        d.update(
            {
                "covariate_names": list(self.covariate_names),
                "n_covariates": len(self.covariate_names),
                "n_mix": int(self.n_mix),
                "T": int(self.A_t.shape[0]),
                "n_classifiers": len(self.classifiers),
                "n_fallback_rows": len(self.fallback_rows),
            }
        )
        return d

    def to_summary_json(self, *, indent: int = 2) -> str:
        """JSON wrapper around :meth:`to_summary_dict`."""
        import json

        return json.dumps(self.to_summary_dict(), indent=indent, default=str)

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter (Phase I.1)."""
        from hmm_core._jupyter import (
            render_chip_list,
            render_matrix_heatmap,
            render_stats_table,
            wrap_html,
        )

        K = self.n_states
        M = self.n_mix
        T = self.A_t.shape[0]
        mask = self.topology.transition_mask()

        stats_rows = [
            ("Topology", self.topology.name),
            ("Regimes (K)", K),
            ("Mixture components per regime (M)", M),
            ("Sequence length (T)", T),
            ("Covariates", render_chip_list(self.covariate_names)),
            ("Logit classifiers fitted", f"{len(self.classifiers)} / {K}"),
            ("Base log-likelihood", f"{self.base.log_likelihood:.3f}"),
            ("Base BIC", f"{self.base.bic:.3f}"),
        ]
        stats_html = render_stats_table(stats_rows)

        # A_t mean heatmap
        A_mean = self.A_t.mean(axis=0)
        heatmap_html = render_matrix_heatmap(
            A_mean,
            self.topology.state_names,
            self.topology.state_names,
            forbidden_mask=mask,
            title="A_t averaged over T",
        )

        # Per-regime sub-mode breakdown (means + weights of the GMM)
        # GMMHMM stores means_ of shape (K, M, D)
        means = np.asarray(self.base.model.means_)  # (K, M, D)
        weights = np.asarray(self.base.model.weights_)  # (K, M)

        # Render a per-regime table : state | component | weight | mean[0]
        rows_html = ["<h5>Sub-modes per regime (GMM components)</h5>"]
        rows_html.append(
            "<table><tr><th>Regime</th><th>Component</th>" "<th>Weight</th><th>Mean (D=0)</th></tr>"
        )
        for k in range(K):
            for m in range(M):
                state_name = self.topology.state_names[k]
                rows_html.append(
                    f"<tr><td>{state_name}</td><td>{m}</td>"
                    f"<td>{weights[k, m]:.3f}</td>"
                    f"<td>{means[k, m, 0]:.3f}</td></tr>"
                )
        rows_html.append("</table>")

        return wrap_html(
            "<h4>GMMNHMMFittedModel</h4>",
            stats_html,
            heatmap_html,
            "".join(rows_html),
            '<div class="small">Two-stage fit : GMM-HMM base + per-source-state '
            "covariate logit. Strategy A from "
            "<code>docs/specs/2026-05-22-phase-a10-gmm-nhmm.md</code>.</div>",
        )


def fit_gmm_nhmm(
    topology: Topology,
    X: np.ndarray,
    Z: np.ndarray,
    *,
    covariate_names: list[str],
    seed: int | None = None,
    lengths: np.ndarray | None = None,
    min_transitions: int = 10,
    regularization: float = 1.0,
) -> GMMNHMMFittedModel:
    """Fit a two-stage GMM-NHMM.

    Parameters
    ----------
    topology : Topology
        Must have ``emission.type == "gmm"``. n_states, n_mix, n_features,
        covariance_type all come from ``topology.emission``.
    X : ndarray, shape (T, n_features)
        Observations.
    Z : ndarray, shape (T, n_covariates)
        Covariates driving transitions.
    covariate_names : list[str]
        Names matching the columns of Z.
    seed : int, optional
        Override topology.init.seed.
    lengths : ndarray, optional
        Sequence lengths for multi-sequence data.
    min_transitions : int, default=10
        Minimum (Z[t], z[t+1]) pairs required to fit logistic regression
        for a given source state. Below this, falls back to the homogeneous
        transmat row from the GMM base.
    regularization : float, default=1.0
        Inverse regularization strength ``C`` for sklearn LogisticRegression.

    Returns
    -------
    GMMNHMMFittedModel
    """
    if topology.emission.type != "gmm":
        raise TopologyError(
            f"fit_gmm_nhmm requires topology.emission.type == 'gmm', "
            f"got {topology.emission.type!r}"
        )
    if Z.shape[0] != X.shape[0]:
        raise ValueError(
            f"X and Z must have same number of rows; got X={X.shape[0]}, Z={Z.shape[0]}"
        )
    if Z.shape[1] != len(covariate_names):
        raise ValueError(
            f"Z has {Z.shape[1]} columns but covariate_names has {len(covariate_names)}"
        )

    # Stage 1: standard GMMHMM fit (homogeneous transitions)
    base = fit(topology, X, seed=seed, lengths=lengths)
    K = base.topology.n_states
    viterbi = base.model.predict(X)
    mask = base.topology.transition_mask()

    # Stage 2: per-source-state logistic regression on covariates
    boundary_idx = _sequence_boundaries(lengths, len(X))
    pairs_t_per_source: dict[int, list[int]] = {i: [] for i in range(K)}
    for t in range(len(viterbi) - 1):
        if t in boundary_idx:
            continue
        i = int(viterbi[t])
        pairs_t_per_source[i].append(t)

    classifiers: dict[int, object] = {}
    fallback_rows: dict[int, np.ndarray] = {}

    actual_seed = seed if seed is not None else topology.init.seed

    for i in range(K):
        ts = pairs_t_per_source[i]
        if len(ts) < min_transitions:
            fallback_rows[i] = base.model.transmat_[i]
            continue
        Z_i = Z[ts]
        next_states = viterbi[np.asarray(ts) + 1]
        unique_targets = np.unique(next_states)
        if len(unique_targets) < 2:
            fallback_rows[i] = base.model.transmat_[i]
            continue
        clf = LogisticRegression(
            C=regularization,
            solver="lbfgs",
            max_iter=200,
            random_state=actual_seed,
        )
        clf.fit(Z_i, next_states)
        classifiers[i] = clf

    # Build A_t: predict next-state probabilities at each t given Z[t]
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
            A_t[:, i, :] = fallback_rows[i]

    # Apply mask + renormalize per (t, i) row
    for t in range(T):
        A_t[t] = _apply_mask(A_t[t], mask)

    return GMMNHMMFittedModel(
        base=base,
        covariate_names=list(covariate_names),
        A_t=A_t,
        classifiers=classifiers,
        fallback_rows=fallback_rows,
    )


def _sequence_boundaries(lengths: np.ndarray | None, total: int) -> set[int]:
    """Return time indices t where (t, t+1) crosses a sequence boundary."""
    if lengths is None:
        return set()
    out: set[int] = set()
    offset = 0
    for L in lengths[:-1]:
        offset += int(L)
        out.add(offset - 1)
    return out
