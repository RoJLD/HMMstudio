"""Model-variant selection: fit several candidate HMM specs and rank them.

Compares candidate models on the SAME observation matrix X by information
criterion (BIC / AIC / HQIC). The hard rule is comparability: plain
``Topology`` candidates model P(X) and are mutually comparable ; NHMM
(P(X|Z)) and Factorial (joint product space) candidates are INCLUDED in
the result table but flagged ``comparable=False`` and never chosen as the
"best by criterion". See docs/specs/2026-05-27-model-variant-selection.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hmm_core.topology import EmissionSpec, Topology


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

    def ranked(self, criterion: str = "bic") -> list[CandidateResult]:
        """Comparable candidates sorted ascending by ``criterion``; errored
        and non-comparable candidates appended after, in original order."""
        if criterion not in ("bic", "aic", "hqic"):
            raise ValueError(f"criterion must be bic/aic/hqic, got {criterion!r}")
        ok = [c for c in self.candidates if c.comparable and c.error is None]
        rest = [c for c in self.candidates if not (c.comparable and c.error is None)]
        ok_sorted = sorted(ok, key=lambda c: getattr(c, criterion))
        return ok_sorted + rest

    def to_summary_dict(self) -> dict:
        return {
            "best_by_bic": self.best_by_bic,
            "best_by_aic": self.best_by_aic,
            "best_by_hqic": self.best_by_hqic,
            "candidates": [
                {
                    "label": c.label,
                    "kind": c.kind,
                    "log_likelihood": c.log_likelihood,
                    "bic": c.bic,
                    "aic": c.aic,
                    "hqic": c.hqic,
                    "n_params": c.n_params,
                    "comparable": c.comparable,
                    "note": c.note,
                    "error": c.error,
                }
                for c in self.candidates
            ],
        }

    def _repr_html_(self) -> str:
        import html as _html

        def fmt(v: float) -> str:
            return "—" if v != v else f"{v:.2f}"  # v!=v catches NaN

        rows = []
        for c in self.ranked("bic"):
            cls = "" if (c.comparable and c.error is None) else ' style="color:#999"'
            best = " ★" if c.label == self.best_by_bic else ""
            note = c.error or c.note or ""
            mark = "" if (c.comparable and c.error is None) else " ⚠"
            rows.append(
                f"<tr{cls}><td>{_html.escape(c.label)}{best}{mark}</td>"
                f"<td>{_html.escape(c.kind)}</td>"
                f"<td style='text-align:right'>{fmt(c.bic)}</td>"
                f"<td style='text-align:right'>{fmt(c.aic)}</td>"
                f"<td style='text-align:right'>{fmt(c.hqic)}</td>"
                f"<td>{_html.escape(note)}</td></tr>"
            )
        header = (
            "<tr><th>candidate</th><th>kind</th><th>BIC</th>"
            "<th>AIC</th><th>HQIC</th><th>note</th></tr>"
        )
        caption = (
            f"<caption style='text-align:left;font-weight:600'>"
            f"Model comparison — best by BIC: {self.best_by_bic or '—'} "
            f"(★ ; ⚠ = not directly comparable)</caption>"
        )
        return (
            "<table style='border-collapse:collapse' border='1' cellpadding='4'>"
            + caption + header + "".join(rows) + "</table>"
        )


def _default_label(kind: str, topology: Topology | None, suffix: str = "") -> str:
    if topology is None:
        return f"{kind}{suffix}"
    base = f"{topology.emission.type} K={topology.n_states}"
    if topology.emission.type == "gmm" and topology.emission.n_mix:
        base += f" n_mix={topology.emission.n_mix}"
    return f"{base}{suffix}"


def _metrics_from_base(base) -> tuple[float, float, float, float, int]:
    """Pull (log_likelihood, bic, aic, hqic, n_params) off a FittedModel."""
    return (
        float(base.log_likelihood),
        float(base.bic),
        float(base.aic),
        float(base.hqic),
        int(base.n_params if hasattr(base, "n_params") else base.to_summary_dict()["n_params"]),
    )


def _fit_candidate(cand: "Candidate", X: np.ndarray, *, seed: int, lengths):
    """Return (kind, fitted, comparable, note). Raises on fit failure."""
    from hmm_core.fit import fit
    from hmm_core.nhmm import fit_nhmm
    from hmm_core.gmm_nhmm import fit_gmm_nhmm
    from hmm_core.factorial_nhmm import fit_factorial_nhmm

    if isinstance(cand, TopologyCandidate):
        fitted = fit(cand.topology, X, seed=seed, lengths=lengths)
        return cand.topology.emission.type, fitted, True, None

    if isinstance(cand, NHMMCandidate):
        if cand.topology.emission.type == "gmm":
            fitted = fit_gmm_nhmm(
                cand.topology, X, cand.Z,
                covariate_names=cand.covariate_names, seed=seed, lengths=lengths,
            )
            kind = "gmm-nhmm"
        else:
            fitted = fit_nhmm(
                cand.topology, X, cand.Z,
                covariate_names=cand.covariate_names, seed=seed, lengths=lengths,
            )
            kind = "nhmm"
        return kind, fitted, False, "models P(X|Z); not directly comparable to P(X) candidates"

    if isinstance(cand, FactorialCandidate):
        fitted = fit_factorial_nhmm(
            cand.chains, X, cand.covariates_per_chain,
            emission=cand.emission,
            covariate_names_per_chain=cand.covariate_names_per_chain,
            seed=seed, lengths=lengths,
        )
        return "factorial", fitted, False, "models a joint product space; n_params differs, not directly comparable"

    raise TypeError(f"unknown candidate type: {type(cand).__name__}")


def compare_models(
    X: np.ndarray,
    candidates: list["Candidate"],
    *,
    lengths: np.ndarray | None = None,
    seed: int = 42,
) -> ModelComparison:
    """Fit each candidate on X and rank the comparable ones by BIC/AIC/HQIC.

    A candidate whose fit raises is captured as a CandidateResult with
    ``error`` set and NaN metrics; it is excluded from every best-by-*.
    """
    results: list[CandidateResult] = []
    for cand in candidates:
        try:
            kind, fitted, comparable, note = _fit_candidate(cand, X, seed=seed, lengths=lengths)
        except Exception as exc:  # noqa: BLE001 — robustness is the point
            kind_guess = type(cand).__name__.replace("Candidate", "").lower()
            label = cand.label or _default_label(kind_guess, getattr(cand, "topology", None))
            results.append(CandidateResult(
                label=label, kind=kind_guess, fitted=None,
                log_likelihood=float("nan"), bic=float("nan"),
                aic=float("nan"), hqic=float("nan"), n_params=0,
                comparable=False, note=None, error=str(exc),
            ))
            continue

        base = fitted.base if hasattr(fitted, "base") else fitted
        ll, bic, aic, hqic, n_params = _metrics_from_base(base)
        topo = getattr(cand, "topology", None)
        label = cand.label or _default_label(kind, topo)
        results.append(CandidateResult(
            label=label, kind=kind, fitted=fitted,
            log_likelihood=ll, bic=bic, aic=aic, hqic=hqic, n_params=n_params,
            comparable=comparable, note=note, error=None,
        ))

    def _best(attr: str) -> str | None:
        pool = [c for c in results if c.comparable and c.error is None]
        if not pool:
            return None
        return min(pool, key=lambda c: getattr(c, attr)).label

    return ModelComparison(
        candidates=results,
        best_by_bic=_best("bic"),
        best_by_aic=_best("aic"),
        best_by_hqic=_best("hqic"),
    )


from dataclasses import replace as _dc_replace  # noqa: E402 — local import keeps auto_grid colocated


def auto_grid(
    base_topology: Topology,
    k_range,
    emission_types: list[str] | None = None,
    *,
    n_mix: int = 2,
) -> list[TopologyCandidate]:
    """Generate the comparable emission × K grid from a base topology.

    Produces only TopologyCandidate (comparable, P(X)). NHMM / Factorial are
    not generated — they need covariates / chain specs the user supplies.

    For each (emission_type, k): a copy of ``base_topology`` with n_states=k,
    state_names s0..s{k-1}, allowed_transitions cleared (ergodic — the grid
    compares model order/family, not topology shape), and the emission type
    swapped. ``n_mix`` is set on gmm candidates.
    """
    emission_types = emission_types or ["gaussian"]
    out: list[TopologyCandidate] = []
    for etype in emission_types:
        for k in k_range:
            e = base_topology.emission
            new_e = _dc_replace(
                e,
                type=etype,
                n_mix=(n_mix if etype == "gmm" else None),
            )
            topo = _dc_replace(
                base_topology,
                n_states=k,
                state_names=[f"s{i}" for i in range(k)],
                allowed_transitions=None,
                emission=new_e,
                emissions=None,  # drop per-state emission hints (K-dependent)
                transmat_prior_matrix=None,  # K-dependent
            )
            out.append(TopologyCandidate(topology=topo))
    return out
