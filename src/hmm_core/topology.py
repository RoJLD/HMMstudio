"""Topology declaration: states, transitions, emission spec, init/fit hyperparams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


class TopologyError(ValueError):
    """Raised when a Topology fails validation."""


@dataclass(frozen=True)
class EmissionSpec:
    type: Literal["gaussian", "gmm", "multinomial", "poisson"]
    n_features: int | None = None
    covariance_type: str | None = None
    n_mix: int | None = None
    n_symbols: int | None = None
    # A.8: optional per-state init hints.  When provided in a list of EmissionSpec
    # via Topology(emissions=[...]), these prime the corresponding state's
    # emission parameters before EM.  The hyperparams (type, n_features,
    # covariance_type, n_mix, n_symbols) must be IDENTICAL across the list.
    init_mean: list[float] | None = None  # gaussian/gmm: (n_features,)
    init_covar: list[list[float]] | None = None  # gaussian/gmm: (n_features, n_features) for full
    init_lambda: list[float] | None = None  # poisson: (n_features,)
    init_emissionprob: list[float] | None = None  # multinomial: (n_symbols,)


@dataclass(frozen=True)
class InitSpec:
    strategy: Literal["uniform", "random", "kmeans", "data_frequencies"]
    seed: int


@dataclass(frozen=True)
class FitSpec:
    algorithm: Literal["baum_welch"]
    n_iter: int
    tol: float
    # Fix #7: optional M-step parameter freezes. When True, the corresponding
    # matrix is NOT re-fit by the backend's M-step; whatever initial value the
    # init strategy produced (or a hand-crafted prior wired in via topology
    # YAML) is preserved through every EM iteration. Emission parameters are
    # always re-fit. Defaults False on both for backward compatibility.
    freeze_startprob: bool = False
    freeze_transmat: bool = False


@dataclass(frozen=True)
class Topology:
    name: str
    n_states: int
    state_names: list[str]
    emission: EmissionSpec
    allowed_transitions: list[tuple[str, str]] | None
    startprob: str | list[float]
    init: InitSpec
    fit: FitSpec
    # A.8: optional per-state emissions.  If provided, MUST have len == n_states
    # and every entry must share the same hyperparams (type, n_features, etc.)
    # as Topology.emission.  Used to seed per-state init hints.
    emissions: list[EmissionSpec] | None = None
    # A.9: optional Dirichlet prior on transitions.
    # - transmat_prior_alpha: scalar symmetric Dirichlet(alpha). Same alpha
    #   on every allowed edge. Equivalent to a full matrix of value `alpha`.
    # - transmat_prior_matrix: explicit (K, K) pseudo-counts. Overrides
    #   `transmat_prior_alpha` when provided. Forbidden edges should have
    #   value 0 (enforced by re-masking).
    transmat_prior_alpha: float | None = None
    transmat_prior_matrix: list[list[float]] | None = None

    def validate(self) -> None:
        if len(self.state_names) != self.n_states:
            raise TopologyError(
                f"state_names has length {len(self.state_names)} but n_states={self.n_states}"
            )
        if len(set(self.state_names)) != len(self.state_names):
            raise TopologyError("state_names must be unique")

        if self.allowed_transitions is not None:
            known = set(self.state_names)
            for src, dst in self.allowed_transitions:
                if src not in known:
                    raise TopologyError(f"unknown state '{src}' in allowed_transitions")
                if dst not in known:
                    raise TopologyError(f"unknown state '{dst}' in allowed_transitions")

        e = self.emission
        if e.type in ("gaussian", "gmm"):
            if e.n_features is None or e.n_features < 1:
                raise TopologyError(f"emission.n_features must be a positive int for {e.type}")
            if e.covariance_type not in ("full", "diag", "tied", "spherical"):
                raise TopologyError(
                    f"emission.covariance_type must be full/diag/tied/spherical for {e.type}"
                )
            if e.type == "gmm" and (e.n_mix is None or e.n_mix < 1):
                raise TopologyError("emission.n_mix must be a positive int for gmm")
        elif e.type == "multinomial":
            if e.n_symbols is None or e.n_symbols < 2:
                raise TopologyError("emission.n_symbols must be >= 2 for multinomial")
        elif e.type == "poisson":
            if e.n_features is None or e.n_features < 1:
                raise TopologyError("emission.n_features must be a positive int for poisson")
        else:
            raise TopologyError(f"unknown emission.type {e.type!r}")

        if isinstance(self.startprob, list):
            if len(self.startprob) != self.n_states:
                raise TopologyError(
                    f"startprob list has length {len(self.startprob)} but n_states={self.n_states}"
                )
            if abs(sum(self.startprob) - 1.0) > 1e-6:
                raise TopologyError("startprob values must sum to 1")
        elif self.startprob not in ("uniform", "first_state"):
            raise TopologyError(
                f"startprob must be 'uniform', 'first_state', or a list of {self.n_states} floats"
            )

        if self.emissions is not None:
            if len(self.emissions) != self.n_states:
                raise TopologyError(
                    f"emissions has length {len(self.emissions)} but n_states={self.n_states}"
                )
            for i, es in enumerate(self.emissions):
                if es.type != self.emission.type:
                    raise TopologyError(
                        f"emissions[{i}].type={es.type!r} does not match "
                        f"emission.type={self.emission.type!r}; "
                        "mixed emission types per state are not yet supported (planned A.8.x)"
                    )
                for field in ("n_features", "covariance_type", "n_mix", "n_symbols"):
                    es_val = getattr(es, field)
                    em_val = getattr(self.emission, field)
                    if es_val is not None and es_val != em_val:
                        raise TopologyError(
                            f"emissions[{i}].{field}={es_val!r} does not match "
                            f"emission.{field}={em_val!r}; "
                            "heterogeneous hyperparams per state are not yet supported (planned A.8.x)"
                        )

        if self.transmat_prior_matrix is not None:
            arr = self.transmat_prior_matrix
            if len(arr) != self.n_states or any(len(row) != self.n_states for row in arr):
                raise TopologyError(
                    f"transmat_prior_matrix must be {self.n_states}×{self.n_states}"
                )
            if any(v < 0 for row in arr for v in row):
                raise TopologyError("transmat_prior_matrix values must be >= 0")
        if self.transmat_prior_alpha is not None and self.transmat_prior_alpha < 0:
            raise TopologyError(
                f"transmat_prior_alpha must be >= 0, got {self.transmat_prior_alpha}"
            )

    def transition_mask(self) -> np.ndarray:
        K = self.n_states
        if self.allowed_transitions is None:
            return np.ones((K, K), dtype=bool)
        index = {name: i for i, name in enumerate(self.state_names)}
        mask = np.zeros((K, K), dtype=bool)
        for src, dst in self.allowed_transitions:
            mask[index[src], index[dst]] = True
        return mask

    def transmat_prior(self) -> np.ndarray | None:
        """Return the K x K prior pseudo-count matrix, or None if no prior set.

        - If ``transmat_prior_matrix`` is set: returns it as ndarray, masked
          (forbidden edges forced to 0).
        - Else if ``transmat_prior_alpha`` is set: returns alpha * mask
          (uniform prior on allowed edges, 0 on forbidden).
        - Else: None.
        """
        mask = self.transition_mask()
        if self.transmat_prior_matrix is not None:
            arr = np.asarray(self.transmat_prior_matrix, dtype=float)
            return arr * mask  # zero forbidden edges
        if self.transmat_prior_alpha is not None:
            return self.transmat_prior_alpha * mask.astype(float)
        return None

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter / IPython (Phase I.1)."""
        from hmm_core._jupyter import (
            render_matrix_heatmap,
            render_stats_table,
            wrap_html,
        )

        mask = self.transition_mask()
        K = self.n_states
        n_allowed = int(mask.sum())

        # Emission details (one-line summary)
        em = self.emission
        emission_summary = em.type
        if em.type in ("gaussian", "gmm") and em.covariance_type:
            emission_summary += f", {em.covariance_type} covariance"
        if em.n_features is not None:
            emission_summary += f", D={em.n_features}"
        if em.type == "gmm" and em.n_mix is not None:
            emission_summary += f", M={em.n_mix}"
        if em.type == "multinomial" and em.n_symbols is not None:
            emission_summary += f", n_symbols={em.n_symbols}"

        stats_rows = [
            ("Topology", self.name),
            ("States (K)", K),
            ("State names", ", ".join(self.state_names)),
            ("Emission", emission_summary),
            ("Allowed edges", f"{n_allowed} / {K * K}"),
            ("Init strategy", f"{self.init.strategy} (seed={self.init.seed})"),
            ("Fit", f"{self.fit.algorithm}, n_iter={self.fit.n_iter}, tol={self.fit.tol}"),
        ]
        if self.transmat_prior_alpha is not None or self.transmat_prior_matrix is not None:
            stats_rows.append(("Transmat prior", "set"))

        stats_html = render_stats_table(stats_rows)

        # Heatmap of mask (binary), forbidden cells crossed
        heatmap_html = render_matrix_heatmap(
            mask.astype(float),
            self.state_names,
            self.state_names,
            forbidden_mask=mask,
            precision=0,
            title="Transition mask (rows = from, cols = to)",
        )

        return wrap_html(
            "<h4>Topology</h4>",
            stats_html,
            heatmap_html,
        )
