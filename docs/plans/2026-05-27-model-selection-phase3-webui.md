# Model-selection Phase 3 — Web UI `/compare` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/compare` web page that fits a comparable emission × K grid on the current dataset and ranks the variants by BIC/AIC/HQIC, reusing the K-scan parent/child job infrastructure.

**Architecture:** The backend reuses the existing parent/child `FitJob` machinery. K-scan children are homogeneous (only `k_override` differs); compare children also vary the emission family, so each child gets two new override fields — `emission_override` and `n_mix_override` — applied at fit time by a helper that mirrors `hmm_core.selection.auto_grid`'s per-cell logic. The fit pipeline (`_run`) and parent-status aggregation (`_update_scan_parent_status`) are reused unchanged. The frontend adds a `/compare` page (start form + polling results table) modeled on `FitPage` + `ScanPage`, and a "Compare" nav entry.

**Tech Stack:** FastAPI + SQLModel (SQLite) backend, React + react-router + Zustand + Tailwind frontend, pytest + FastAPI TestClient.

**Spec:** `docs/specs/2026-05-27-model-variant-selection.md` (Phase 3 section). Resolves spec open question #2 (reuse the jobs table with per-child override fields, not a new parent type).

**Prerequisites (shipped):** Phase 1 core (`auto_grid`, comparability rule), Phase 2 CLI, HQIC in `summary.json` (`get_status` already surfaces `hqic`), K-scan parent/child infra (`submit_scan`, `_run`, `_update_scan_parent_status`, `ScanPage`).

---

## Design notes (read before starting)

- **Comparable-only, v1.** The web grid generates only `TopologyCandidate`-equivalent children (Gaussian / GMM / Poisson — all model P(X)). NHMM / Factorial are NOT offered in the UI (they need explicit covariates / chain specs). A note on the page points to the Python API / `hmm-fit compare`.
- **Reuse `_run`.** Each compare child stores the base `topology` YAML + `k_override` (the K) + `emission_override` (the emission family) + `n_mix_override` (for GMM). `_run` applies them at load time via `_topology_with_overridden_emission`, which mirrors `auto_grid` exactly (clears `allowed_transitions` / per-state `emissions` / `transmat_prior_matrix`, sets ergodic state names `s0..s{k-1}`, swaps `emission.type` + `n_mix`). Proven logic — Phase 1's `auto_grid` does the same replace.
- **Reuse `_update_scan_parent_status`.** It is generic over `parent_id` children; compare parents work with it as-is. No new aggregation helper.
- **Label scheme** (matches `selection._default_label`): `"gaussian K=3"`, `"gmm K=2 n_mix=2"`, `"poisson K=4"`. Used as the stable identifier for `best_label_by_*` and frontend row highlighting (each (emission, K) is unique in a grid).
- **DB schema evolution.** `db.py` uses bare `SQLModel.metadata.create_all`, which creates missing tables but never alters existing ones. Fresh DBs get the new columns automatically; existing DBs need an additive `ALTER TABLE ADD COLUMN` (SQLite supports this cheaply). Task 1 adds an idempotent guard so the feature works without forcing users to delete their jobs DB.
- **Poisson hint.** Poisson expects count data; on continuous floats a Poisson child will fail and show as a `failed` row (non-fatal) — acceptable, and the form notes it.

## File Structure

**Backend:**
- Modify: `src/hmm_studio/server/models.py` — add `emission_override`, `n_mix_override` to `FitJob`.
- Modify: `src/hmm_studio/server/db.py` — `_ensure_fitjob_columns` additive migration + call it in `create_db_engine`.
- Modify: `src/hmm_studio/server/jobs.py` — `_topology_with_overridden_emission` helper, `submit_compare`, extend `_run` Step 2.
- Modify: `src/hmm_studio/server/schemas.py` — `CompareModelCreate`, `CompareChildStatus`, `CompareResult`.
- Modify: `src/hmm_studio/server/app.py` — `_compare_label` helper, `POST /api/fit/compare/start`, `GET /api/fit/compare/{parent_id}`.

**Frontend:**
- Modify: `src/hmm_studio/frontend/src/api/client.ts` — types + `startCompare` / `getCompare`.
- Create: `src/hmm_studio/frontend/src/pages/ComparePage.tsx` — start form (no `:parentId`) + results table (`:parentId`).
- Modify: `src/hmm_studio/frontend/src/App.tsx` — two routes.
- Modify: `src/hmm_studio/frontend/src/components/Layout.tsx` — "Compare" nav entry.

**Tests:**
- Modify: `tests/studio/test_jobs.py` — migration + `submit_compare` grid tests.
- Modify: `tests/studio/test_endpoints.py` — compare start/status + grid-generation tests.

---

### Task 1: FitJob compare columns + additive migration

**Files:**
- Modify: `src/hmm_studio/server/models.py` (add two fields to `FitJob`, near `k_override`)
- Modify: `src/hmm_studio/server/db.py`
- Test: `tests/studio/test_jobs.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/studio/test_jobs.py`:

```python
def test_create_db_engine_has_compare_columns(tmp_path):
    from sqlalchemy import text
    from hmm_studio.server.db import create_db_engine
    from hmm_studio.server.models import FitJob

    eng = create_db_engine(tmp_path / "s.db")
    with eng.connect() as conn:
        cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({FitJob.__tablename__})"))}
    assert {"emission_override", "n_mix_override"} <= cols


def test_migration_adds_compare_columns_to_legacy_table(tmp_path):
    from sqlalchemy import create_engine, text
    from hmm_studio.server.db import _ensure_fitjob_columns
    from hmm_studio.server.models import FitJob

    table = FitJob.__tablename__
    eng = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with eng.begin() as conn:
        conn.execute(text(f"CREATE TABLE {table} (id VARCHAR PRIMARY KEY, k_override INTEGER)"))
    _ensure_fitjob_columns(eng)  # should be idempotent + additive
    _ensure_fitjob_columns(eng)  # second call is a no-op
    with eng.connect() as conn:
        cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
    assert "emission_override" in cols and "n_mix_override" in cols
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/studio/test_jobs.py::test_create_db_engine_has_compare_columns tests/studio/test_jobs.py::test_migration_adds_compare_columns_to_legacy_table -v`
Expected: FAIL — `_ensure_fitjob_columns` does not exist (ImportError) / columns absent.

- [ ] **Step 3: Add the model fields**

In `src/hmm_studio/server/models.py`, in the `FitJob` class, immediately after the `k_override` field, add:

```python
    emission_override: str | None = Field(default=None)  # compare: per-child emission family
    n_mix_override: int | None = Field(default=None)  # compare: GMM mixture count (gmm children only)
```

- [ ] **Step 4: Add the additive migration in db.py**

In `src/hmm_studio/server/db.py`, change the imports and `create_db_engine`, and add the helper:

```python
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text

# Import models so SQLModel.metadata picks them up.
from hmm_studio.server import models  # noqa: F401
from hmm_studio.server.models import FitJob


def _ensure_fitjob_columns(engine) -> None:
    """Additively add compare-mode columns to an existing fitjob table.

    SQLModel.create_all() creates missing TABLES but never alters existing
    ones, so a DB created before the compare feature lacks emission_override /
    n_mix_override. SQLite supports cheap additive ALTERs; add any missing.
    Idempotent: a no-op once the columns exist.
    """
    table = FitJob.__tablename__
    wanted = {"emission_override": "VARCHAR", "n_mix_override": "INTEGER"}
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        for name, sqltype in wanted.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}"))


def create_db_engine(db_path: str | Path):
    """Create a SQLite engine and ensure tables exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    _ensure_fitjob_columns(engine)
    return engine
```

(Keep the existing `get_session` unchanged.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/studio/test_jobs.py::test_create_db_engine_has_compare_columns tests/studio/test_jobs.py::test_migration_adds_compare_columns_to_legacy_table -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/hmm_studio/server/models.py src/hmm_studio/server/db.py tests/studio/test_jobs.py
git commit -m "feat(studio): FitJob emission_override/n_mix_override + additive migration"
```
(End message with the `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` trailer.)

---

### Task 2: `submit_compare` + emission-override fit path

**Files:**
- Modify: `src/hmm_studio/server/jobs.py` (add `_topology_with_overridden_emission` near `_topology_with_overridden_k`; add `submit_compare` after `submit_scan`; extend `_run` Step 2)
- Test: `tests/studio/test_jobs.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/studio/test_jobs.py`:

```python
def test_submit_compare_creates_grid_children(setup_env):
    import time
    from sqlmodel import select
    from hmm_studio.server.models import FitJob

    runner = JobRunner(setup_env["engine"], setup_env["results_dir"])
    try:
        parent_id = runner.submit_compare(
            topology_yaml=VALID_TOPOLOGY_YAML,
            dataset_id=setup_env["dataset_id"],
            k_min=2,
            k_max=3,
            emission_types=["gaussian", "gmm"],
            n_mix=2,
            seed=42,
        )
        deadline = time.time() + 90
        while time.time() < deadline:
            with get_session(setup_env["engine"]) as s:
                children = list(
                    s.exec(select(FitJob).where(FitJob.parent_id == parent_id)).all()
                )
                done = children and all(
                    str(getattr(c.status, "value", c.status)) in ("done", "failed")
                    for c in children
                )
            if done:
                break
            time.sleep(0.25)

        with get_session(setup_env["engine"]) as s:
            children = list(s.exec(select(FitJob).where(FitJob.parent_id == parent_id)).all())
            combos = {(c.emission_override, c.k_override) for c in children}
            n_mix_by_emission = {
                c.emission_override: c.n_mix_override for c in children
            }
        assert combos == {("gaussian", 2), ("gaussian", 3), ("gmm", 2), ("gmm", 3)}
        assert n_mix_by_emission["gmm"] == 2
        assert n_mix_by_emission["gaussian"] is None
    finally:
        runner.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/studio/test_jobs.py::test_submit_compare_creates_grid_children -v`
Expected: FAIL — `JobRunner` has no `submit_compare`.

- [ ] **Step 3: Add the emission-override helper**

In `src/hmm_studio/server/jobs.py`, after `_topology_with_overridden_k`, add:

```python
def _topology_with_overridden_emission(
    topology: Topology, emission_type: str, new_k: int, n_mix: int | None
) -> Topology:
    """Return a copy of `topology` with emission family + n_states overridden.

    Mirrors hmm_core.selection.auto_grid's per-cell logic: swap emission.type
    (and n_mix for gmm), set n_states=new_k with ergodic s0..s{k-1} state names,
    and drop the K-dependent fields (allowed_transitions, per-state emissions,
    transmat prior). n_features / covariance_type carry over from the base.
    """
    from dataclasses import replace

    new_emission = replace(
        topology.emission,
        type=emission_type,
        n_mix=(n_mix if emission_type == "gmm" else None),
    )
    return replace(
        topology,
        n_states=new_k,
        state_names=[f"s{i}" for i in range(new_k)],
        allowed_transitions=None,
        emission=new_emission,
        emissions=None,
        transmat_prior_matrix=None,
    )
```

- [ ] **Step 4: Add `submit_compare` to `JobRunner`**

In `src/hmm_studio/server/jobs.py`, add this method right after `submit_scan` (inside the `JobRunner` class):

```python
    def submit_compare(
        self,
        topology_yaml: str,
        dataset_id: str,
        k_min: int,
        k_max: int,
        emission_types: list[str],
        n_mix: int = 2,
        seed: int | None = None,
        lengths: list[int] | None = None,
    ) -> str:
        """Create a parent + one child per (emission_type, K) cell.

        Each child models P(X) (comparable grid). Children reuse the base
        topology YAML and override emission family + K at fit time.
        """
        if k_min < 1 or k_max < k_min:
            raise ValueError(f"invalid k range: k_min={k_min}, k_max={k_max}")
        if not emission_types:
            raise ValueError("emission_types must be non-empty")

        with get_session(self._engine) as session:
            parent = FitJob(
                topology=topology_yaml,
                dataset_id=dataset_id,
                seed=seed,
                status=FitJobStatus.QUEUED,
                lengths=json.dumps(lengths) if lengths else "",
            )
            session.add(parent)
            session.commit()
            session.refresh(parent)
            parent_id = parent.id

        for etype in emission_types:
            for k in range(k_min, k_max + 1):
                with get_session(self._engine) as session:
                    child = FitJob(
                        topology=topology_yaml,
                        dataset_id=dataset_id,
                        seed=seed,
                        status=FitJobStatus.QUEUED,
                        lengths=json.dumps(lengths) if lengths else "",
                        parent_id=parent_id,
                        k_override=k,
                        emission_override=etype,
                        n_mix_override=(n_mix if etype == "gmm" else None),
                    )
                    session.add(child)
                    session.commit()
                    session.refresh(child)
                    child_id = child.id
                future = self._executor.submit(self._run, child_id)
                with self._lock:
                    self._futures[child_id] = future

        with get_session(self._engine) as session:
            parent = session.get(FitJob, parent_id)
            parent.status = FitJobStatus.RUNNING
            parent.started_at = utcnow()
            session.add(parent)
            session.commit()

        return parent_id
```

- [ ] **Step 5: Extend `_run` Step 2 to apply the emission override**

In `src/hmm_studio/server/jobs.py`, in `_run`, the Step 1 snapshot block reads job fields. Add two lines after `k_override = job.k_override`:

```python
                k_override = job.k_override  # NEW: K-scan override
                emission_override = job.emission_override  # NEW: compare emission override
                n_mix_override = job.n_mix_override  # NEW: compare gmm n_mix
                job_parent_id = job.parent_id  # NEW: scan parent tracking (overrides outer None)
```

Then replace the Step 2 topology-override block:

```python
            # Step 2: validate topology, possibly with overridden K
            try:
                topology = _load_topology_from_yaml_str(topology_yaml)
                if k_override is not None and k_override != topology.n_states:
                    topology = _topology_with_overridden_k(topology, k_override)
                    topology.validate()
            except Exception as exc:
```

with:

```python
            # Step 2: validate topology, possibly with overridden emission / K
            try:
                topology = _load_topology_from_yaml_str(topology_yaml)
                if emission_override is not None:
                    topology = _topology_with_overridden_emission(
                        topology,
                        emission_override,
                        k_override if k_override is not None else topology.n_states,
                        n_mix_override,
                    )
                    topology.validate()
                elif k_override is not None and k_override != topology.n_states:
                    topology = _topology_with_overridden_k(topology, k_override)
                    topology.validate()
            except Exception as exc:
```

(The `except` body and the rest of `_run` are unchanged — `_update_scan_parent_status` already fires for any `job_parent_id`.)

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/studio/test_jobs.py::test_submit_compare_creates_grid_children -v`
Expected: PASS (4 children with the right (emission, K) combos; gmm carries n_mix, gaussian does not).

- [ ] **Step 7: Commit**

```bash
git add src/hmm_studio/server/jobs.py tests/studio/test_jobs.py
git commit -m "feat(studio): submit_compare fits an emission x K grid via override fields"
```

---

### Task 3: compare schemas + REST endpoints

**Files:**
- Modify: `src/hmm_studio/server/schemas.py` (add three models after `ScanResult`)
- Modify: `src/hmm_studio/server/app.py` (add `_compare_label` + two routes; import the new schemas)
- Test: `tests/studio/test_endpoints.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/studio/test_endpoints.py`:

```python
def test_compare_start_and_status(client):
    r = client.post(
        "/api/data/upload",
        files={"file": ("d.csv", _make_csv_bytes(), "text/csv")},
    )
    dataset_id = r.json()["id"]
    r = client.post(
        "/api/fit/compare/start",
        json={
            "topology_yaml": VALID_TOPOLOGY,
            "dataset_id": dataset_id,
            "k_min": 2,
            "k_max": 3,
            "emission_types": ["gaussian", "gmm"],
            "n_mix": 2,
            "seed": 42,
        },
    )
    assert r.status_code == 200, r.text
    parent_id = r.json()["parent_id"]

    cmp = {}
    for _ in range(200):
        cmp = client.get(f"/api/fit/compare/{parent_id}").json()
        if cmp["overall_status"] in ("done", "failed"):
            break
        time.sleep(0.25)

    assert cmp["overall_status"] == "done", cmp
    assert len(cmp["children"]) == 4
    labels = {c["label"] for c in cmp["children"]}
    assert "gaussian K=2" in labels
    assert "gmm K=2 n_mix=2" in labels
    assert cmp["best_label_by_bic"] in labels


def test_compare_grid_generation(client):
    r = client.post(
        "/api/data/upload",
        files={"file": ("d.csv", _make_csv_bytes(), "text/csv")},
    )
    dataset_id = r.json()["id"]
    r = client.post(
        "/api/fit/compare/start",
        json={
            "topology_yaml": VALID_TOPOLOGY,
            "dataset_id": dataset_id,
            "k_min": 2,
            "k_max": 4,
            "emission_types": ["gaussian"],
            "seed": 42,
        },
    )
    assert r.status_code == 200, r.text
    parent_id = r.json()["parent_id"]
    cmp = client.get(f"/api/fit/compare/{parent_id}").json()
    assert {c["k"] for c in cmp["children"]} == {2, 3, 4}
    assert all(c["emission"] == "gaussian" for c in cmp["children"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/studio/test_endpoints.py::test_compare_start_and_status tests/studio/test_endpoints.py::test_compare_grid_generation -v`
Expected: FAIL — `/api/fit/compare/start` returns 404 (route not defined).

- [ ] **Step 3: Add the schemas**

In `src/hmm_studio/server/schemas.py`, after `ScanResult`, add:

```python
class CompareModelCreate(BaseModel):
    """Launch a model comparison: one child fit per (emission_type, K) cell."""

    topology_yaml: str
    dataset_id: str
    k_min: int
    k_max: int
    emission_types: list[str]  # comparable families: gaussian | gmm | poisson
    n_mix: int = 2  # for gmm candidates
    seed: int | None = None
    lengths: list[int] | None = None


class CompareChildStatus(BaseModel):
    """One candidate's status in a comparison."""

    job_id: str
    label: str  # "gaussian K=3", "gmm K=2 n_mix=2"
    emission: str
    k: int
    n_mix: int | None = None
    status: str
    log_likelihood: float | None = None
    bic: float | None = None
    aic: float | None = None
    hqic: float | None = None
    converged: bool | None = None
    n_iter_actual: int | None = None
    error: str | None = None


class CompareResult(BaseModel):
    parent_id: str
    overall_status: str  # "queued" | "running" | "done" | "failed"
    children: list[CompareChildStatus]
    best_label_by_bic: str | None = None
    best_label_by_aic: str | None = None
    best_label_by_hqic: str | None = None
```

- [ ] **Step 4: Add the endpoints + label helper in app.py**

In `src/hmm_studio/server/app.py`, add `CompareModelCreate`, `CompareChildStatus`, `CompareResult` to the existing schemas import. Then add (next to the scan endpoints):

```python
def _compare_label(emission: str, k: int, n_mix: int | None) -> str:
    base = f"{emission} K={k}"
    if emission == "gmm" and n_mix:
        base += f" n_mix={n_mix}"
    return base


@app.post("/api/fit/compare/start", response_model=dict)
def start_compare(req: CompareModelCreate):
    with get_session(engine) as session:
        ds = session.get(Dataset, req.dataset_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="dataset not found")
    try:
        parent_id = runner.submit_compare(
            topology_yaml=req.topology_yaml,
            dataset_id=req.dataset_id,
            k_min=req.k_min,
            k_max=req.k_max,
            emission_types=req.emission_types,
            n_mix=req.n_mix,
            seed=req.seed,
            lengths=req.lengths,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"parent_id": parent_id}


@app.get("/api/fit/compare/{parent_id}", response_model=CompareResult)
def get_compare(parent_id: str):
    from sqlmodel import select

    with get_session(engine) as session:
        parent = session.get(FitJob, parent_id)
        if parent is None or parent.parent_id is not None:
            raise HTTPException(status_code=404, detail="compare parent not found")
        parent_status = parent.status
        raw_children = [
            {
                "id": c.id,
                "k": c.k_override,
                "emission": c.emission_override,
                "n_mix": c.n_mix_override,
            }
            for c in session.exec(select(FitJob).where(FitJob.parent_id == parent_id)).all()
        ]

    raw_children.sort(key=lambda x: (x["emission"] or "", x["k"] or 0))

    child_statuses = []
    for c in raw_children:
        ch = runner.get_status(c["id"])
        child_statuses.append(
            CompareChildStatus(
                job_id=c["id"],
                label=_compare_label(c["emission"] or "", c["k"] or 0, c["n_mix"]),
                emission=c["emission"] or "",
                k=c["k"] or 0,
                n_mix=c["n_mix"],
                status=ch["status"],
                log_likelihood=ch.get("log_likelihood"),
                bic=ch.get("bic"),
                aic=ch.get("aic"),
                hqic=ch.get("hqic"),
                converged=ch.get("converged"),
                n_iter_actual=ch.get("n_iter_actual"),
                error=ch.get("error"),
            )
        )

    def _best(attr: str) -> str | None:
        done = [c for c in child_statuses if c.status == "done" and getattr(c, attr) is not None]
        return min(done, key=lambda c: getattr(c, attr)).label if done else None

    if parent_status == FitJobStatus.RUNNING:
        statuses = [c.status for c in child_statuses]
        if not statuses or any(s in ("queued", "running") for s in statuses):
            overall = "running"
        elif all(s == "failed" for s in statuses):
            overall = "failed"
        else:
            overall = "done"
    else:
        overall = parent_status.value if hasattr(parent_status, "value") else str(parent_status)

    return CompareResult(
        parent_id=parent_id,
        overall_status=overall,
        children=child_statuses,
        best_label_by_bic=_best("bic"),
        best_label_by_aic=_best("aic"),
        best_label_by_hqic=_best("hqic"),
    )
```

Note: `FitJob`, `Dataset`, `FitJobStatus`, `HTTPException`, `get_session`, `engine`, `runner` are already imported/defined in `app.py` (used by the scan endpoints) — verify and reuse; do not redefine.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/studio/test_endpoints.py::test_compare_start_and_status tests/studio/test_endpoints.py::test_compare_grid_generation -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/hmm_studio/server/schemas.py src/hmm_studio/server/app.py tests/studio/test_endpoints.py
git commit -m "feat(studio): /api/fit/compare start + status endpoints"
```

---

### Task 4: frontend API client

**Files:**
- Modify: `src/hmm_studio/frontend/src/api/client.ts` (add after the scan types/functions)

- [ ] **Step 1: Add types + functions**

In `src/hmm_studio/frontend/src/api/client.ts`, after `getScan`, add:

```typescript
export interface CompareChildStatus {
  job_id: string;
  label: string;
  emission: string;
  k: number;
  n_mix: number | null;
  status: string;
  log_likelihood: number | null;
  bic: number | null;
  aic: number | null;
  hqic: number | null;
  converged: boolean | null;
  n_iter_actual: number | null;
  error: string | null;
}

export interface CompareResult {
  parent_id: string;
  overall_status: string;
  children: CompareChildStatus[];
  best_label_by_bic: string | null;
  best_label_by_aic: string | null;
  best_label_by_hqic: string | null;
}

export async function startCompare(params: {
  topology_yaml: string;
  dataset_id: string;
  k_min: number;
  k_max: number;
  emission_types: string[];
  n_mix?: number;
  seed?: number;
  lengths?: number[];
}): Promise<{ parent_id: string }> {
  return jsonFetch<{ parent_id: string }>("/api/fit/compare/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getCompare(parentId: string): Promise<CompareResult> {
  return jsonFetch<CompareResult>(`/api/fit/compare/${parentId}`);
}
```

(`jsonFetch` is the helper the existing `startScan`/`getScan` use — reuse it, do not redefine.)

- [ ] **Step 2: Type-check**

Run (from `src/hmm_studio/frontend`): `npm run lint`
Expected: no errors (this is `tsc --noEmit`).

- [ ] **Step 3: Commit**

```bash
git add src/hmm_studio/frontend/src/api/client.ts
git commit -m "feat(ui): compare API client (startCompare/getCompare + types)"
```

---

### Task 5: ComparePage (start form + results table)

**Files:**
- Create: `src/hmm_studio/frontend/src/pages/ComparePage.tsx`

- [ ] **Step 1: Create the page**

Create `src/hmm_studio/frontend/src/pages/ComparePage.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTopologyStore } from "../store/topologyStore";
import { useDatasetStore } from "../store/datasetStore";
import { topologyToYAML } from "../lib/yaml";
import {
  startCompare,
  getCompare,
  type CompareResult,
} from "../api/client";

const EMISSION_CHOICES = ["gaussian", "gmm", "poisson"] as const;

export default function ComparePage() {
  const { parentId } = useParams<{ parentId: string }>();
  return parentId ? <CompareResults parentId={parentId} /> : <CompareForm />;
}

function CompareForm() {
  const dataset = useDatasetStore((s) => s.current);
  const states = useTopologyStore((s) => s.states);
  const navigate = useNavigate();

  const [emissions, setEmissions] = useState<string[]>(["gaussian"]);
  const [nMix, setNMix] = useState(2);
  const [kMin, setKMin] = useState(2);
  const [kMax, setKMax] = useState(5);
  const [seed, setSeed] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nCells = emissions.length * Math.max(0, kMax - kMin + 1);
  const canSubmit =
    !!dataset && states.length > 0 && emissions.length > 0 && kMax >= kMin && !submitting;

  function toggleEmission(e: string, on: boolean) {
    setEmissions((cur) => (on ? [...cur, e] : cur.filter((x) => x !== e)));
  }

  async function handleLaunch() {
    if (!dataset) return;
    setError(null);
    setSubmitting(true);
    try {
      const yamlText = topologyToYAML(useTopologyStore.getState());
      const r = await startCompare({
        topology_yaml: yamlText,
        dataset_id: dataset.id,
        k_min: kMin,
        k_max: kMax,
        emission_types: emissions,
        n_mix: nMix,
        seed: seed === "" ? undefined : Number(seed),
      });
      navigate(`/compare/${r.parent_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "compare failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">Compare models</h2>
      <p className="text-slate-600 mb-6">
        Fit a grid of comparable emission families × K on the current dataset and
        rank them by BIC / AIC / HQIC. All candidates model{" "}
        <span className="font-mono">P(X)</span>, so the information criteria are
        directly comparable.
      </p>

      <div className="space-y-4 mb-6">
        <Status label="Topology" ok={states.length > 0}>
          {states.length > 0
            ? `${states.length} states (used as the base; emission + K are swept)`
            : "no topology — go to the Topology editor first"}
        </Status>
        <Status label="Dataset" ok={!!dataset}>
          {dataset
            ? `${dataset.filename} (${dataset.n_rows} × ${dataset.n_cols})`
            : "no dataset — upload one on the Data page"}
        </Status>
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Emission families</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {EMISSION_CHOICES.map((e) => (
            <label
              key={e}
              className="flex items-center gap-1.5 text-sm px-2 py-1 border border-slate-200 rounded cursor-pointer hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={emissions.includes(e)}
                onChange={(ev) => toggleEmission(e, ev.target.checked)}
              />
              <span className="font-mono">{e}</span>
            </label>
          ))}
        </div>
        {emissions.includes("gmm") && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-slate-600">n_mix (GMM)</span>
            <input
              type="number"
              min={2}
              value={nMix}
              onChange={(e) => setNMix(parseInt(e.target.value, 10) || 2)}
              className="border border-slate-300 rounded px-2 py-1 w-16"
            />
          </label>
        )}
        {emissions.includes("poisson") && (
          <p className="text-xs text-amber-700 mt-2">
            Poisson expects integer count data; on continuous data those
            candidates will be reported as failed.
          </p>
        )}
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-slate-600">k_min</span>
            <input
              type="number"
              min={1}
              value={kMin}
              onChange={(e) => setKMin(parseInt(e.target.value, 10) || 1)}
              className="border border-slate-300 rounded px-2 py-1 w-16"
            />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-slate-600">k_max</span>
            <input
              type="number"
              min={kMin}
              value={kMax}
              onChange={(e) => setKMax(parseInt(e.target.value, 10) || 1)}
              className="border border-slate-300 rounded px-2 py-1 w-16"
            />
          </label>
          <span className="text-xs text-slate-500">{nCells} fits will run in parallel</span>
        </div>
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <label className="flex items-center gap-3 text-sm">
          <span className="text-slate-700 w-24">Seed (override)</span>
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(e.target.value === "" ? "" : parseInt(e.target.value, 10))}
            placeholder="(use topology default)"
            className="border border-slate-300 rounded px-2 py-1 text-sm flex-1"
          />
        </label>
      </div>

      <button
        type="button"
        disabled={!canSubmit}
        onClick={handleLaunch}
        className={
          "px-4 py-2 rounded text-sm font-medium " +
          (canSubmit
            ? "bg-brand-600 text-white hover:bg-brand-700"
            : "bg-slate-200 text-slate-500 cursor-not-allowed")
        }
      >
        {submitting ? "Submitting…" : "Launch comparison"}
      </button>

      {error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <p className="mt-4 text-xs text-slate-500">
        NHMM / Factorial variants are not offered here — they need explicit
        covariates / chain specs. Use the Python API (
        <span className="font-mono">hmm_core.compare_models</span>) or{" "}
        <span className="font-mono">hmm-fit compare</span> for those.
      </p>
    </div>
  );
}

function CompareResults({ parentId }: { parentId: string }) {
  const [cmp, setCmp] = useState<CompareResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await getCompare(parentId);
        if (!cancelled) setCmp(r);
        if (r.overall_status === "running" || r.overall_status === "queued") {
          setTimeout(poll, 500);
        }
      } catch {
        // ignore transient errors
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [parentId]);

  if (!cmp) {
    return (
      <div className="text-slate-600">
        Loading comparison <code>{parentId}</code>...
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">
        Model comparison{" "}
        <span className="text-sm font-mono text-slate-500">{cmp.parent_id}</span>
      </h2>
      <p className="text-slate-600 mb-4">
        Status: <Badge status={cmp.overall_status} />
        {cmp.best_label_by_bic && (
          <span className="ml-3 text-sm">
            Best by BIC: <strong className="font-mono">{cmp.best_label_by_bic}</strong>
          </span>
        )}
        {cmp.best_label_by_aic && (
          <span className="ml-3 text-sm">
            Best by AIC: <strong className="font-mono">{cmp.best_label_by_aic}</strong>
          </span>
        )}
        {cmp.best_label_by_hqic && (
          <span className="ml-3 text-sm">
            Best by HQIC: <strong className="font-mono">{cmp.best_label_by_hqic}</strong>
          </span>
        )}
      </p>

      <div className="border border-slate-200 rounded-md bg-white overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-slate-700">candidate</th>
              <th className="text-left px-3 py-2 font-medium text-slate-700">emission</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">K</th>
              <th className="text-left px-3 py-2 font-medium text-slate-700">Status</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">log-lik</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">BIC</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">AIC</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">HQIC</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {cmp.children.map((c) => (
              <tr key={c.job_id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono font-semibold">{c.label}</td>
                <td className="px-3 py-2 font-mono">{c.emission}</td>
                <td className="px-3 py-2 text-right font-mono">{c.k}</td>
                <td className="px-3 py-2">
                  <Badge status={c.status} />
                </td>
                <td className="px-3 py-2 text-right font-mono">{fmt(c.log_likelihood)}</td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.label === cmp.best_label_by_bic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.bic)}
                </td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.label === cmp.best_label_by_aic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.aic)}
                </td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.label === cmp.best_label_by_hqic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.hqic)}
                </td>
                <td className="px-3 py-2 text-right">
                  {c.status === "done" && (
                    <Link
                      to={`/results/${c.job_id}`}
                      className="text-indigo-600 hover:underline text-xs"
                    >
                      view →
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Status({
  label,
  ok,
  children,
}: {
  label: string;
  ok: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-3 text-sm">
      <span
        className={
          "inline-block w-5 h-5 rounded-full text-center leading-5 text-xs font-bold " +
          (ok ? "bg-green-500 text-white" : "bg-slate-300 text-slate-600")
        }
      >
        {ok ? "✓" : "?"}
      </span>
      <span className="text-slate-700 font-medium w-24">{label}</span>
      <span className="text-slate-600">{children}</span>
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-slate-200 text-slate-800",
    running: "bg-blue-100 text-blue-800",
    done: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    cancelled: "bg-amber-100 text-amber-800",
  };
  return (
    <span
      className={
        "inline-block px-2 py-0.5 rounded text-xs font-medium " +
        (colors[status] ?? "bg-slate-200 text-slate-800")
      }
    >
      {status}
    </span>
  );
}

function fmt(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return v.toFixed(2);
}
```

- [ ] **Step 2: Type-check**

Run (from `src/hmm_studio/frontend`): `npm run lint`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/hmm_studio/frontend/src/pages/ComparePage.tsx
git commit -m "feat(ui): ComparePage — emission x K grid form + ranked results table"
```

---

### Task 6: routes + nav entry

**Files:**
- Modify: `src/hmm_studio/frontend/src/App.tsx`
- Modify: `src/hmm_studio/frontend/src/components/Layout.tsx`

- [ ] **Step 1: Register the routes**

In `src/hmm_studio/frontend/src/App.tsx`, add the import and two routes (place them next to the `scan/:parentId` route):

```tsx
import ComparePage from "./pages/ComparePage";
```

```tsx
        <Route path="compare" element={<ComparePage />} />
        <Route path="compare/:parentId" element={<ComparePage />} />
```

- [ ] **Step 2: Add the nav entry**

In `src/hmm_studio/frontend/src/components/Layout.tsx`, add `Compare` to `NAV_MAIN`:

```tsx
const NAV_MAIN = [
  { to: "/", label: "Home" },
  { to: "/data", label: "Data" },
  { to: "/fit", label: "Fit" },
  { to: "/compare", label: "Compare" },
  { to: "/topology", label: "Topology editor" },
] as const;
```

(The existing `navLink` active-state logic already highlights `/compare` and `/compare/:parentId` via its `startsWith(to + "/")` check.)

- [ ] **Step 3: Type-check**

Run (from `src/hmm_studio/frontend`): `npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/hmm_studio/frontend/src/App.tsx src/hmm_studio/frontend/src/components/Layout.tsx
git commit -m "feat(ui): wire /compare route + Compare nav entry"
```

---

### Task 7: full backend suite + frontend build + docs

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/specs/2026-05-27-model-variant-selection.md` (mark Phase 3 done; resolve open question #2)

- [ ] **Step 1: Run the studio backend tests**

Run: `python -m pytest tests/studio/test_jobs.py tests/studio/test_endpoints.py -q`
Expected: all pass (existing scan/fit tests + the new compare tests).

- [ ] **Step 2: Build the frontend**

Run (from `src/hmm_studio/frontend`): `npm run build`
Expected: `tsc` clean + `vite build` produces a bundle with no errors.

- [ ] **Step 3: Update CHANGELOG**

In `CHANGELOG.md`, under `[Unreleased]` → `### Added`:

```markdown
- Web UI **Compare** page (`/compare`): fit a comparable emission × K grid
  (Gaussian / GMM / Poisson) on the current dataset and rank candidates by
  BIC / AIC / HQIC, reusing the K-scan parent/child engine. Backed by
  `POST /api/fit/compare/start` + `GET /api/fit/compare/{id}`. NHMM/Factorial
  remain Python-API / `hmm-fit compare` only.
```

- [ ] **Step 4: Update the spec (code change ⇒ spec update, per workspace rule)**

In `docs/specs/2026-05-27-model-variant-selection.md`, append an update section:

```markdown
## Update 2026-05-27 — Phase 3 shipped

Phase 3 (web UI `/compare`) implemented. Open question #2 resolved: the jobs
table is **reused** (no new parent type). Compare children carry two new
override fields — `emission_override`, `n_mix_override` — alongside the
existing `k_override`; `_run` applies them via `_topology_with_overridden_emission`
(mirrors `auto_grid`). `_update_scan_parent_status` is reused for aggregation.
Best candidate is identified by label (`best_label_by_{bic,aic,hqic}`), since
K alone is not unique across emission families. Web v1 = comparable grid only,
as specified.
```

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md docs/specs/2026-05-27-model-variant-selection.md
git commit -m "docs(studio): changelog + spec update for /compare (Phase 3)"
```

---

## Definition of done (Phase 3, per spec §6)

- [ ] `POST /api/fit/compare/start` + `GET /api/fit/compare/{id}` + schemas.
- [ ] `/compare` page (form + results) + Compare nav entry + client.ts.
- [ ] ≥ 2 endpoint tests green (`test_compare_start_and_status`, `test_compare_grid_generation`); migration + `submit_compare` jobs tests green.
- [ ] Full `tests/studio/` green; `npm run build` clean (tsc + bundle).
- [ ] CHANGELOG `[Unreleased]` updated; spec amended (open question #2 resolved).

## Out of scope (deferred)

- NHMM / Factorial in the web UI (covariates/chains can't be expressed in the grid form) — Python API / CLI only.
- e2e Playwright test for `/compare` — spec marks it optional; skip in v1 unless asked.
- A BIC/AIC scatter for compare (the K-scan `BicScatter` is K-indexed; a variant-indexed chart is a later nicety).

## Self-review

- **Spec coverage:** Phase 3 backend (`/api/fit/compare/*`, reuse K-scan infra, per-child kind via override fields), frontend (`/compare` form + results table + best badges + nav), comparable-only-with-note → Tasks 1-7. Spec-required tests (`test_compare_start_and_status`, `test_compare_grid_generation`) present in Task 3. ✓
- **Placeholder scan:** every step shows complete code; no TBDs. ✓
- **Type consistency:** backend `best_label_by_{bic,aic,hqic}` (str) ↔ frontend `CompareResult.best_label_by_*` (string | null); `CompareChildStatus` fields identical across Pydantic (Task 3) and TS (Task 4); `submit_compare` signature identical across jobs (Task 2) and the endpoint call (Task 3); override fields `emission_override`/`n_mix_override` consistent across models (Task 1), jobs (Task 2), and endpoint reads (Task 3). Label scheme (`"gmm K=2 n_mix=2"`) identical in `_compare_label` (backend) and asserted in tests. ✓
- **Reuse check:** `_run`, `_update_scan_parent_status`, `get_status`, `jsonFetch`, `Status`/`Badge`/`fmt` patterns reused, not reinvented. ✓
