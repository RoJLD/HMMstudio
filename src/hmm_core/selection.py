"""Model-variant selection: fit several candidate HMM specs and rank them.

Compares candidate models on the SAME observation matrix X by information
criterion (BIC / AIC / HQIC). The hard rule is comparability: plain
``Topology`` candidates model P(X) and are mutually comparable ; NHMM
(P(X|Z)) and Factorial (joint product space) candidates are INCLUDED in
the result table but flagged ``comparable=False`` and never chosen as the
"best by criterion". See docs/specs/2026-05-27-model-variant-selection.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


@dataclass(frozen=True)
class TopologyCandidate:
    """A comparable candidate: a plain Topology fit via hmm_core.fit (models P(X))."""

    topology: Topology
    label: str | None = None  # defaults to "<emission> K=<n_states>"


@dataclass(frozen=True)
class NHMMCandidate:
    """A non-comparable candidate: NHMM / GMM-NHMM (models P(X|Z))."""

    topology: Topology
    Z: np.ndarray
    covariate_names: list[str]
    label: str | None = None


@dataclass(frozen=True)
class FactorialCandidate:
    """A non-comparable candidate: Factorial NHMM (joint product space)."""

    chains: list  # list[FactorialChainSpec]
    covariates_per_chain: dict
    emission: EmissionSpec
    covariate_names_per_chain: dict | None = None
    label: str | None = None


Candidate = TopologyCandidate | NHMMCandidate | FactorialCandidate


@dataclass(frozen=True)
class CandidateResult:
    """One candidate's fitted metrics within a comparison."""

    label: str
    kind: str
    fitted: object  # FittedModel | NHMMFittedModel | GMMNHMMFittedModel | FactorialNHMMFittedModel | None
    log_likelihood: float
    bic: float
    aic: float
    hqic: float
    n_params: int
    comparable: bool
    note: str | None = None
    error: str | None = None  # set (and metrics NaN) if the fit raised


@dataclass(frozen=True)
class ModelComparison:
    """Outcome of compare_models: every candidate + best-by-criterion."""

    candidates: list[CandidateResult]
    best_by_bic: str | None
    best_by_aic: str | None
    best_by_hqic: str | None
