# Model-variant selection — Phase 1 (core Python) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Python core of model-variant selection — `compare_models(X, candidates)` that fits multiple candidate HMM specs on the same data and ranks them by BIC/AIC/HQIC, flagging NHMM/Factorial as non-comparable.

**Architecture:** A new pure-Python module `src/hmm_core/selection.py`. Candidate specs are a small union of frozen dataclasses (`TopologyCandidate`, `NHMMCandidate`, `FactorialCandidate`). `compare_models` dispatches each candidate to the right existing fit entry-point (`fit` / `fit_nhmm` / `fit_gmm_nhmm` / `fit_factorial_nhmm`), extracts metrics, and returns a `ModelComparison` whose "best by criterion" considers only `comparable=True` candidates. No new dependencies, no new backend.

**Tech Stack:** Python, numpy, the existing `hmm_core.fit` / `nhmm` / `gmm_nhmm` / `factorial_nhmm` engines, pytest.

**Spec:** `docs/specs/2026-05-27-model-variant-selection.md` (§ 3 Phase 1, § 5 Phase 1 tests).

**Comparability rule (load-bearing):** plain `Topology` candidates model `P(X)` → `comparable=True`. `NHMMCandidate` / `FactorialCandidate` model `P(X|Z)` / a joint product space → `comparable=False`, included in the table but excluded from every `best_by_*`.

**Metric source:** `fit()` returns a `FittedModel` with `.bic/.aic/.hqic/.n_params/.log_likelihood` directly. The variant fits (`fit_nhmm`, `fit_gmm_nhmm`, `fit_factorial_nhmm`) return wrappers exposing `.base: FittedModel` — read metrics from `.base`.

---

### Task 1: Candidate + result dataclasses

**Files:**
- Create: `src/hmm_core/selection.py`
- Test: `tests/test_selection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_selection.py
from __future__ import annotations

import numpy as np

from hmm_core.selection import (
    TopologyCandidate,
    NHMMCandidate,
    FactorialCandidate,
    CandidateResult,
    ModelComparison,
)
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology


def _gaussian_topo(name: str, k: int) -> Topology:
    return Topology(
        name=name,
        n_states=k,
        state_names=[f"s{i}" for i in range(k)],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-3),
    )


def test_candidate_dataclasses_construct():
    c = TopologyCandidate(topology=_gaussian_topo("g2", 2))
    assert c.topology.n_states == 2
    # CandidateResult is a plain record; comparable defaults are explicit
    r = CandidateResult(
        label="gaussian K=2",
        kind="gaussian",
        fitted=None,
        log_likelihood=-10.0,
        bic=30.0,
        aic=25.0,
        hqic=27.0,
        n_params=5,
        comparable=True,
        note=None,
        error=None,
    )
    assert r.comparable is True
    mc = ModelComparison(candidates=[r], best_by_bic="gaussian K=2", best_by_aic="gaussian K=2", best_by_hqic="gaussian K=2")
    assert mc.candidates[0].label == "gaussian K=2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py::test_candidate_dataclasses_construct -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hmm_core.selection'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/hmm_core/selection.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py::test_candidate_dataclasses_construct -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hmm_core/selection.py tests/test_selection.py
git commit -m "feat(selection): candidate + result dataclasses for model comparison"
```

---

### Task 2: `compare_models` — fit, extract metrics, rank

**Files:**
- Modify: `src/hmm_core/selection.py`
- Test: `tests/test_selection.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_selection.py
import warnings
import pytest
from hmm_core.selection import compare_models


def _three_regime_data(seed=0):
    rng = np.random.default_rng(seed)
    return np.vstack([
        rng.normal(-3.0, 0.4, (80, 1)),
        rng.normal(0.0, 0.4, (80, 1)),
        rng.normal(3.0, 0.4, (80, 1)),
    ])


def test_compare_ranks_comparable_by_bic():
    X = _three_regime_data()
    cands = [TopologyCandidate(_gaussian_topo(f"g{k}", k)) for k in (2, 3, 4)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    # all three are comparable Gaussian fits
    assert all(c.comparable for c in cmp.candidates)
    # best_by_bic is the label of the minimum-BIC candidate
    comparable = [c for c in cmp.candidates if c.error is None]
    expected = min(comparable, key=lambda c: c.bic).label
    assert cmp.best_by_bic == expected


def test_failed_candidate_excluded_not_fatal():
    X = _three_regime_data()
    # A topology asking for more features than the data has -> fit raises.
    bad = _gaussian_topo("bad", 2)
    bad = Topology(
        name="bad", n_states=2, state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=5),
        allowed_transitions=None, startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=10, tol=1e-3),
    )
    cands = [TopologyCandidate(_gaussian_topo("g2", 2)), TopologyCandidate(bad)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    labels = {c.label: c for c in cmp.candidates}
    # the good one ranks; the bad one has an error and is excluded from best
    assert cmp.best_by_bic == "gaussian K=2"
    bad_result = [c for c in cmp.candidates if c.error is not None]
    assert len(bad_result) == 1
    assert np.isnan(bad_result[0].bic)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py -k "ranks_comparable or failed_candidate" -v`
Expected: FAIL with `ImportError: cannot import name 'compare_models'`

- [ ] **Step 3: Implement `compare_models` + helpers**

Append to `src/hmm_core/selection.py`:

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py -k "ranks_comparable or failed_candidate" -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add src/hmm_core/selection.py tests/test_selection.py
git commit -m "feat(selection): compare_models fits + ranks comparable candidates, robust to fit failures"
```

---

### Task 3: NHMM / Factorial flagged non-comparable

**Files:**
- Test: `tests/test_selection.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_selection.py
def test_nhmm_flagged_and_never_best():
    rng = np.random.default_rng(1)
    X = _three_regime_data(1)
    Z = rng.normal(0, 1, (len(X), 1))
    cands = [
        TopologyCandidate(_gaussian_topo("g3", 3)),
        NHMMCandidate(_gaussian_topo("nhmm3", 3), Z=Z, covariate_names=["z"]),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    nhmm = [c for c in cmp.candidates if c.kind == "nhmm"][0]
    assert nhmm.comparable is False
    assert nhmm.note and "P(X|Z)" in nhmm.note
    # best is always the comparable Gaussian, never the NHMM
    assert cmp.best_by_bic == "gaussian K=3"
    assert cmp.best_by_aic == "gaussian K=3"
    assert cmp.best_by_hqic == "gaussian K=3"


def test_factorial_flagged_not_comparable():
    from hmm_core.factorial_nhmm import FactorialChainSpec
    rng = np.random.default_rng(2)
    X = rng.normal(0, 1, (300, 2))
    chains = [FactorialChainSpec(name="a", n_states=2), FactorialChainSpec(name="b", n_states=2)]
    fc = FactorialCandidate(
        chains=chains,
        covariates_per_chain={"a": rng.normal(0, 1, (300, 1)), "b": rng.normal(0, 1, (300, 1))},
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
    )
    cands = [TopologyCandidate(_gaussian_topo("g2", 2)), fc]
    # NOTE: g2 topo is 1-feature; make a 2-feature one to match X
    cands[0] = TopologyCandidate(Topology(
        name="g2d", n_states=2, state_names=["a", "b"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
        allowed_transitions=None, startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=0),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    ))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    fac = [c for c in cmp.candidates if c.kind == "factorial"]
    assert len(fac) == 1
    assert fac[0].comparable is False
    assert fac[0].note and "joint" in fac[0].note.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py -k "nhmm_flagged or factorial_flagged" -v`
Expected: FAIL (the behaviour exists from Task 2, but these tests are new — if Task 2 was implemented correctly they may PASS immediately; if so, that is acceptable for these flagging tests since they assert already-implemented behaviour. If they fail, fix `_fit_candidate` notes/comparable flags.)

- [ ] **Step 3: (only if a test failed) adjust `_fit_candidate`**

No code change expected if Task 2 set `comparable`/`note` correctly. If a note assertion fails, align the note strings in `_fit_candidate` with the substrings asserted (`"P(X|Z)"`, `"joint"`).

- [ ] **Step 4: Run to verify it passes**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py -k "nhmm_flagged or factorial_flagged" -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add tests/test_selection.py
git commit -m "test(selection): NHMM and Factorial flagged non-comparable, never chosen best"
```

---

### Task 4: `auto_grid` helper

**Files:**
- Modify: `src/hmm_core/selection.py`
- Test: `tests/test_selection.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_selection.py
from hmm_core.selection import auto_grid


def test_auto_grid_generates_emission_x_k():
    base = _gaussian_topo("base", 3)
    grid = auto_grid(base, k_range=range(2, 5), emission_types=["gaussian", "gmm"], n_mix=2)
    # 3 K values x 2 emission types = 6 candidates
    assert len(grid) == 6
    assert all(isinstance(c, TopologyCandidate) for c in grid)
    ks = sorted({c.topology.n_states for c in grid})
    assert ks == [2, 3, 4]
    types = {c.topology.emission.type for c in grid}
    assert types == {"gaussian", "gmm"}
    # gmm candidates carry n_mix
    gmm = [c for c in grid if c.topology.emission.type == "gmm"]
    assert all(c.topology.emission.n_mix == 2 for c in gmm)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py::test_auto_grid_generates_emission_x_k -v`
Expected: FAIL with `ImportError: cannot import name 'auto_grid'`

- [ ] **Step 3: Implement `auto_grid`**

Append to `src/hmm_core/selection.py`:

```python
from dataclasses import replace as _dc_replace


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
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py::test_auto_grid_generates_emission_x_k -v`
Expected: PASS

If it fails because `Topology` / `EmissionSpec` have different field names (e.g. no `emissions` or `transmat_prior_matrix`), open `src/hmm_core/topology.py`, read the dataclass fields, and adjust the `_dc_replace` kwargs to match exactly. Re-run.

- [ ] **Step 5: Commit**

```bash
git add src/hmm_core/selection.py tests/test_selection.py
git commit -m "feat(selection): auto_grid generates the comparable emission x K grid"
```

---

### Task 5: `to_summary_dict` + `_repr_html_` on ModelComparison

**Files:**
- Modify: `src/hmm_core/selection.py`
- Test: `tests/test_selection.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_selection.py
import json


def test_to_summary_dict_is_json_serialisable():
    X = _three_regime_data()
    cands = auto_grid(_gaussian_topo("base", 3), range(2, 4), ["gaussian"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    d = cmp.to_summary_dict()
    assert "candidates" in d and "best_by_bic" in d
    assert len(d["candidates"]) == 2
    # round-trips through json
    json.loads(json.dumps(d))


def test_repr_html_marks_noncomparable():
    rng = np.random.default_rng(3)
    X = _three_regime_data(3)
    Z = rng.normal(0, 1, (len(X), 1))
    cands = [
        TopologyCandidate(_gaussian_topo("g3", 3)),
        NHMMCandidate(_gaussian_topo("nhmm3", 3), Z=Z, covariate_names=["z"]),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cmp = compare_models(X, cands, seed=0)
    html = cmp._repr_html_()
    assert isinstance(html, str) and len(html) > 50
    assert "<table" in html
    # the non-comparable row carries a visible marker
    assert "not directly comparable" in html or "⚠" in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py -k "summary_dict or repr_html" -v`
Expected: FAIL with `AttributeError: 'ModelComparison' object has no attribute 'to_summary_dict'`

- [ ] **Step 3: Implement the methods on `ModelComparison`**

Replace the `ModelComparison` dataclass body in `src/hmm_core/selection.py` with a version that adds the two methods (keep the fields):

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py -k "summary_dict or repr_html" -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add src/hmm_core/selection.py tests/test_selection.py
git commit -m "feat(selection): ModelComparison.to_summary_dict + ranked + _repr_html_"
```

---

### Task 6: Top-level exports + CHANGELOG

**Files:**
- Modify: `src/hmm_core/__init__.py`
- Modify: `CHANGELOG.md`
- Test: `tests/test_selection.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_selection.py
def test_top_level_exports():
    import hmm_core
    assert hasattr(hmm_core, "compare_models")
    assert hasattr(hmm_core, "auto_grid")
    assert hasattr(hmm_core, "ModelComparison")
    assert hasattr(hmm_core, "TopologyCandidate")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py::test_top_level_exports -v`
Expected: FAIL with `AssertionError` (no `compare_models` attribute)

- [ ] **Step 3: Add exports**

In `src/hmm_core/__init__.py`, add after the existing `from hmm_core.regimes import ...` line:

```python
from hmm_core.selection import (
    Candidate,
    CandidateResult,
    FactorialCandidate,
    ModelComparison,
    NHMMCandidate,
    TopologyCandidate,
    auto_grid,
    compare_models,
)
```

And add to `__all__` (keep it sorted-ish, matching the existing style):

```python
    "Candidate",
    "CandidateResult",
    "FactorialCandidate",
    "ModelComparison",
    "NHMMCandidate",
    "TopologyCandidate",
    "auto_grid",
    "compare_models",
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv\Scripts\python -m pytest tests/test_selection.py::test_top_level_exports -v`
Expected: PASS

- [ ] **Step 5: Update CHANGELOG**

Add a new section under `## [Unreleased]` in `CHANGELOG.md`, near the other `hmm_core` additions:

```markdown
### Added — model-variant selection (Phase 1: Python core)

- New `hmm_core.selection` module (exported at package top level):
  - `compare_models(X, candidates, *, lengths=None, seed=42) -> ModelComparison`
    — fits each candidate HMM spec on the same `X` and ranks the comparable
    ones by BIC / AIC / HQIC. Robust: a candidate whose fit raises is captured
    with an `error` and NaN metrics, never fatal to the comparison.
  - Candidate types: `TopologyCandidate` (comparable, models P(X)),
    `NHMMCandidate` and `FactorialCandidate` (flagged `comparable=False` —
    they model P(X|Z) / a joint product space, so they appear in the table
    but are never chosen as "best by criterion").
  - `auto_grid(base_topology, k_range, emission_types, n_mix=2)` — generates
    the comparable emission × K grid.
  - `ModelComparison` with `.ranked(criterion)`, `.to_summary_dict()`, and a
    Jupyter `_repr_html_` (non-comparable rows greyed + ⚠).
- Phase 1 of `docs/specs/2026-05-27-model-variant-selection.md`. CLI
  (`hmm-fit compare`) and the `/compare` web page are Phases 2-3.
- The in-scope, HMM-only slice of the Nathan/Robin ModelFinder.
```

- [ ] **Step 6: Commit**

```bash
git add src/hmm_core/__init__.py CHANGELOG.md tests/test_selection.py
git commit -m "feat(selection): export model-comparison API at top level + CHANGELOG"
```

---

### Task 7: Full-suite regression check

**Files:** none (verification only)

- [ ] **Step 1: Run the full hmm_core + studio suite**

Run: `.venv\Scripts\python -m pytest tests/ --ignore=tests/test_jupyter_repr.py -q`
Expected: all pass (prior count + 8 new selection tests). 3 skips on `HMM_VALENTIN_ETH_PATH` are expected.

- [ ] **Step 2: If green, Phase 1 is done.** No commit (nothing changed). Report the new test count and that Phase 1 core is ready for Phase 2 (CLI).

---

## Self-review notes

- **Spec coverage (§3 Phase 1):** `compare_models` (Task 2), candidate union (Task 1), `auto_grid` (Task 4), `CandidateResult`/`ModelComparison` + `_repr_html_`/`to_summary_dict` (Tasks 1, 5), comparability rule + best-among-comparable (Tasks 2, 3), robustness to failed fits (Task 2), top-level export (Task 6). All § Phase 1 test rows from spec § 5 are covered (ranks, best-only-among-comparable, nhmm flagged, factorial flagged, auto_grid, failed-candidate, repr_html, to_summary_dict).
- **Known field-name risk:** Task 4's `auto_grid` uses `dataclasses.replace` on `Topology` with kwargs `emissions=None` and `transmat_prior_matrix=None`. If those exact field names differ in `topology.py`, Step 4 instructs reading the dataclass and adjusting. This is the one place to verify against the real `Topology` definition before trusting the code verbatim.
- **GMM-NHMM routing:** `_fit_candidate` routes an `NHMMCandidate` whose topology emission is `gmm` to `fit_gmm_nhmm` (kind `"gmm-nhmm"`), else `fit_nhmm`. Both flagged non-comparable.
- Phases 2 (CLI) and 3 (web UI) are separate plans, written when Phase 1 lands.
