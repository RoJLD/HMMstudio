# B.1 Backend FastAPI skeleton — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend skeleton for `hmm-studio` (sub-project B), with SQLite persistence and REST endpoints for topology validation, data upload, and fit job orchestration. WebSocket streaming (B.2) and frontend (B.3+) are NOT in this plan — only the Python backend.

**Architecture:** FastAPI + SQLModel (SQLite) + ThreadPoolExecutor for fit jobs. Lives in `src/hmm_studio/server/` (sibling of `src/hmm_core/`). Consumes `hmm_core.fit` for the actual ML work. CLI entry point `hmm-studio serve` launches uvicorn.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, uvicorn, python-multipart (for uploads), pytest + httpx (testing). Hard dependency on `hmm_core` (already in the same repo).

**Spec context:** `docs/specs/2026-05-21-hmm-studio-web-design.md` + `docs/decisions/0002-b-stack-decisions.md`.

**Working directory:** `C:\Users\rdenis\VScode\Tools\hmm_studio\`. Activate venv: `.\.venv\Scripts\Activate.ps1`.

---

## Task B.1.1: Add backend dependencies + package skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `src/hmm_studio/__init__.py`
- Create: `src/hmm_studio/server/__init__.py`

- [ ] **Step 1.1: Update `pyproject.toml`**

Read the current `pyproject.toml`. Add a `web` optional-dependencies group:

```toml
web = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.16",
    "python-multipart>=0.0.9",
    "httpx>=0.27",  # used by FastAPI's TestClient via starlette
]
```

In the `[project.scripts]` section, ADD (don't replace):
```toml
hmm-studio = "hmm_studio.cli:app"
```

In `[tool.setuptools.packages.find]`, no change needed — `where = ["src"]` already discovers `hmm_studio` alongside `hmm_core`.

- [ ] **Step 1.2: Create package skeleton**

`src/hmm_studio/__init__.py`:
```python
"""hmm-studio: web UI for hmm-core (sub-project B)."""

__version__ = "0.1.0"
```

`src/hmm_studio/server/__init__.py`:
```python
"""FastAPI backend for hmm-studio."""
```

- [ ] **Step 1.3: Install**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[web,dev]"
```

Expected: fastapi, sqlmodel, uvicorn, python-multipart installed.

- [ ] **Step 1.4: Commit**

```bash
git add pyproject.toml src/hmm_studio/
git commit -m "feat(studio): backend deps + empty package skeleton"
```

---

## Task B.1.2: Database models (SQLModel)

**Files:**
- Create: `src/hmm_studio/server/db.py`
- Create: `src/hmm_studio/server/models.py`
- Create: `tests/studio/__init__.py` (empty)
- Create: `tests/studio/test_models.py`

- [ ] **Step 2.1: Write failing tests**

Create `tests/studio/__init__.py` (empty file).

`tests/studio/test_models.py`:

```python
"""Tests for SQLModel persistence: datasets, fit_jobs."""

from __future__ import annotations

import json
from datetime import datetime

from hmm_studio.server.db import create_db_engine, get_session
from hmm_studio.server.models import Dataset, FitJob, FitJobStatus


def test_dataset_roundtrip(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    with get_session(engine) as session:
        ds = Dataset(
            filename="foo.csv",
            n_rows=100,
            n_cols=3,
            dtypes=json.dumps({"f0": "float64", "f1": "float64", "f2": "float64"}),
            path=str(tmp_path / "uploads" / "abc.csv"),
        )
        session.add(ds)
        session.commit()
        session.refresh(ds)
        assert ds.id is not None
        assert isinstance(ds.created_at, datetime)


def test_fit_job_roundtrip(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    with get_session(engine) as session:
        ds = Dataset(filename="x.csv", n_rows=10, n_cols=2,
                     dtypes="{}", path="/tmp/x.csv")
        session.add(ds)
        session.commit()
        session.refresh(ds)

        job = FitJob(
            topology=json.dumps({"name": "t", "n_states": 3}),
            dataset_id=ds.id,
            seed=42,
            status=FitJobStatus.QUEUED,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.id is not None
        assert job.status == FitJobStatus.QUEUED
        assert job.dataset_id == ds.id


def test_fit_job_status_transitions(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    with get_session(engine) as session:
        ds = Dataset(filename="x.csv", n_rows=10, n_cols=2,
                     dtypes="{}", path="/tmp/x.csv")
        session.add(ds)
        session.commit()
        session.refresh(ds)
        job = FitJob(topology="{}", dataset_id=ds.id, status=FitJobStatus.QUEUED)
        session.add(job)
        session.commit()
        session.refresh(job)

        # Transition to running
        job.status = FitJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        session.add(job)
        session.commit()

        # Transition to done
        job.status = FitJobStatus.DONE
        job.ended_at = datetime.utcnow()
        job.result_path = "/tmp/result/"
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.status == FitJobStatus.DONE
        assert job.result_path == "/tmp/result/"


def test_database_creates_tables_on_first_use(tmp_path):
    db_path = tmp_path / "fresh.db"
    assert not db_path.exists()
    engine = create_db_engine(db_path)
    assert db_path.exists()
    # Tables should be queryable.
    with get_session(engine) as session:
        result = session.query(Dataset).all()
        assert result == []
```

- [ ] **Step 2.2: Run tests — confirm import failures**

```powershell
pytest tests/studio/test_models.py -v
```

Expected: 4 ImportError failures.

- [ ] **Step 2.3: Implement `src/hmm_studio/server/models.py`**

```python
"""SQLModel database schema for hmm-studio backend."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class FitJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Dataset(SQLModel, table=True):
    """An uploaded CSV dataset, with metadata and a filesystem path."""

    id: str = Field(default_factory=_uuid_str, primary_key=True)
    filename: str
    n_rows: int
    n_cols: int
    dtypes: str = ""  # JSON-serialized {col: dtype} map
    path: str = ""    # filesystem path to the uploaded CSV
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FitJob(SQLModel, table=True):
    """A fit job: topology + dataset + execution metadata."""

    id: str = Field(default_factory=_uuid_str, primary_key=True)
    topology: str = ""  # JSON-serialized Topology
    dataset_id: str = Field(foreign_key="dataset.id")
    seed: int | None = None
    status: FitJobStatus = Field(default=FitJobStatus.QUEUED)
    progress: str = ""  # JSON list of log-likelihoods per iteration
    result_path: str | None = None  # filesystem path to results bundle
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2.4: Implement `src/hmm_studio/server/db.py`**

```python
"""Database engine + session management for hmm-studio."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.engine.base import Engine

# Import the models so SQLModel.metadata picks them up.
from hmm_studio.server import models  # noqa: F401


def create_db_engine(db_path: str | Path) -> Engine:
    """Create a SQLite engine and ensure tables exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def get_session(engine: Engine) -> Iterator[Session]:
    """Yield a session bound to ``engine``; commits or rolls back on exit."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

- [ ] **Step 2.5: Run tests — confirm pass**

```powershell
pytest tests/studio/test_models.py -v
```

Expected: 4 passes.

- [ ] **Step 2.6: Full suite check**

```powershell
pytest -q
```

Expected: 70 passes total (66 prior + 4 new). No regression in hmm-core tests.

- [ ] **Step 2.7: Commit**

```bash
git add src/hmm_studio/server/db.py src/hmm_studio/server/models.py tests/studio/
git commit -m "feat(studio): SQLModel schema for Dataset + FitJob persistence"
```

---

## Task B.1.3: Pydantic schemas for request/response

**Files:**
- Create: `src/hmm_studio/server/schemas.py`
- Create: `tests/studio/test_schemas.py`

- [ ] **Step 3.1: Write failing tests**

`tests/studio/test_schemas.py`:

```python
"""Tests for Pydantic request/response schemas."""

from __future__ import annotations

import pytest

from hmm_studio.server.schemas import (
    DatasetPreview,
    FitJobCreate,
    FitJobResult,
    FitJobStatusOut,
    TopologyValidateRequest,
    TopologyValidateResponse,
)


def test_topology_validate_request_minimal():
    req = TopologyValidateRequest(yaml_content="name: foo\nn_states: 2\n")
    assert req.yaml_content.startswith("name:")


def test_topology_validate_response_ok():
    resp = TopologyValidateResponse(valid=True, error=None, summary="ok")
    assert resp.valid is True


def test_topology_validate_response_error():
    resp = TopologyValidateResponse(valid=False, error="missing required field: 'emission'", summary=None)
    assert resp.valid is False
    assert "missing" in resp.error


def test_dataset_preview_shape():
    preview = DatasetPreview(
        id="abc123",
        filename="data.csv",
        n_rows=100,
        n_cols=3,
        columns=["f0", "f1", "f2"],
        dtypes={"f0": "float64", "f1": "float64", "f2": "float64"},
        head=[{"f0": 1.0, "f1": 2.0, "f2": 3.0}],
    )
    assert preview.n_rows == 100
    assert preview.head[0]["f0"] == 1.0


def test_fit_job_create_validation():
    req = FitJobCreate(topology_yaml="name: t\nn_states: 2", dataset_id="abc", seed=42)
    assert req.seed == 42

    req_no_seed = FitJobCreate(topology_yaml="...", dataset_id="abc")
    assert req_no_seed.seed is None


def test_fit_job_status_out():
    status = FitJobStatusOut(
        id="job123",
        status="running",
        progress=[-1000.0, -900.0, -850.0],
        log_likelihood=None,
        bic=None,
        error=None,
    )
    assert len(status.progress) == 3


def test_fit_job_result_done():
    result = FitJobResult(
        id="job123",
        status="done",
        log_likelihood=-850.0,
        bic=1750.0,
        aic=1720.0,
        n_iter_actual=12,
        converged=True,
        result_path="/path/to/results",
    )
    assert result.converged is True
```

- [ ] **Step 3.2: Run tests — confirm failures**

```powershell
pytest tests/studio/test_schemas.py -v
```

Expected: 7 ImportError failures.

- [ ] **Step 3.3: Implement `src/hmm_studio/server/schemas.py`**

```python
"""Pydantic schemas for FastAPI request/response bodies."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# Topology
class TopologyValidateRequest(BaseModel):
    yaml_content: str


class TopologyValidateResponse(BaseModel):
    valid: bool
    error: str | None = None
    summary: str | None = None  # human-readable: "valid: name (n_states=K, ...)"


# Dataset
class DatasetPreview(BaseModel):
    id: str
    filename: str
    n_rows: int
    n_cols: int
    columns: list[str]
    dtypes: dict[str, str]
    head: list[dict[str, Any]]  # first N rows as records


# Fit job
class FitJobCreate(BaseModel):
    topology_yaml: str
    dataset_id: str
    seed: int | None = None


class FitJobStatusOut(BaseModel):
    id: str
    status: str
    progress: list[float] = Field(default_factory=list)
    log_likelihood: float | None = None
    bic: float | None = None
    error: str | None = None


class FitJobResult(BaseModel):
    id: str
    status: str
    log_likelihood: float | None = None
    bic: float | None = None
    aic: float | None = None
    n_iter_actual: int | None = None
    converged: bool | None = None
    result_path: str | None = None
    error: str | None = None
```

- [ ] **Step 3.4: Run tests — confirm pass**

```powershell
pytest tests/studio/test_schemas.py -v
```

Expected: 7 passes.

- [ ] **Step 3.5: Commit**

```bash
git add src/hmm_studio/server/schemas.py tests/studio/test_schemas.py
git commit -m "feat(studio): Pydantic request/response schemas"
```

---

## Task B.1.4: Job runner (ThreadPoolExecutor + fit orchestration)

**Files:**
- Create: `src/hmm_studio/server/jobs.py`
- Create: `tests/studio/test_jobs.py`

- [ ] **Step 4.1: Write failing tests**

`tests/studio/test_jobs.py`:

```python
"""Tests for the in-process fit job runner."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hmm_studio.server.db import create_db_engine, get_session
from hmm_studio.server.jobs import JobRunner
from hmm_studio.server.models import Dataset, FitJob, FitJobStatus


VALID_TOPOLOGY_YAML = """
name: test
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 20, tol: 1.0e-4}
"""


@pytest.fixture
def setup_env(tmp_path):
    """Create engine, dataset on disk, results dir."""
    engine = create_db_engine(tmp_path / "studio.db")
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    # Generate a small dataset
    rng = np.random.default_rng(42)
    X = np.vstack([
        rng.normal(loc=-2.0, scale=0.3, size=(100, 2)),
        rng.normal(loc=0.0, scale=0.3, size=(100, 2)),
        rng.normal(loc=2.0, scale=0.3, size=(100, 2)),
    ])
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(csv_path, index=False)

    with get_session(engine) as s:
        ds = Dataset(
            filename="data.csv", n_rows=300, n_cols=2,
            dtypes=json.dumps({"f0": "float64", "f1": "float64"}),
            path=str(csv_path),
        )
        s.add(ds)
        s.commit()
        s.refresh(ds)
        dataset_id = ds.id

    return {"engine": engine, "results_dir": results_dir, "dataset_id": dataset_id}


def test_submit_runs_and_finishes(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    job_id = runner.submit(
        topology_yaml=VALID_TOPOLOGY_YAML,
        dataset_id=setup_env["dataset_id"],
        seed=42,
    )
    # Wait for the job to finish (max 30s).
    for _ in range(300):
        status = runner.get_status(job_id)
        if status["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    runner.shutdown()
    final = runner.get_status(job_id)
    assert final["status"] == "done", final
    assert final["log_likelihood"] is not None
    assert final["bic"] is not None


def test_submit_invalid_topology_fails(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    job_id = runner.submit(
        topology_yaml="not: a valid: topology",  # malformed
        dataset_id=setup_env["dataset_id"],
        seed=42,
    )
    for _ in range(50):
        status = runner.get_status(job_id)
        if status["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    runner.shutdown()
    final = runner.get_status(job_id)
    assert final["status"] == "failed", final
    assert final["error"] is not None


def test_progress_updates_during_fit(setup_env):
    """Progress should be a non-empty list of log-likelihoods after the fit."""
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    job_id = runner.submit(
        topology_yaml=VALID_TOPOLOGY_YAML,
        dataset_id=setup_env["dataset_id"],
        seed=42,
    )
    for _ in range(300):
        status = runner.get_status(job_id)
        if status["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    runner.shutdown()
    final = runner.get_status(job_id)
    assert final["status"] == "done"
    # progress list is updated by the runner from model.monitor_.history.
    assert len(final["progress"]) > 0
    # Should be monotonically (mostly) increasing — log-lik improves over EM.
    progress = final["progress"]
    assert progress[-1] >= progress[0] - 1e-3  # tiny tolerance for numerical noise


def test_result_path_contains_artifacts(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    job_id = runner.submit(
        topology_yaml=VALID_TOPOLOGY_YAML,
        dataset_id=setup_env["dataset_id"],
        seed=42,
    )
    for _ in range(300):
        status = runner.get_status(job_id)
        if status["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    runner.shutdown()
    final = runner.get_status(job_id)
    result_dir = Path(final["result_path"])
    assert (result_dir / "model.pkl").exists()
    assert (result_dir / "summary.json").exists()
    assert (result_dir / "fit_log.txt").exists()
```

- [ ] **Step 4.2: Run — expect failures**

```powershell
pytest tests/studio/test_jobs.py -v
```

Expected: 4 ImportError failures.

- [ ] **Step 4.3: Implement `src/hmm_studio/server/jobs.py`**

```python
"""In-process job runner for hmm-studio fits.

Each `submit()` schedules a fit on a ThreadPoolExecutor. The fit's progress
(monitor_.history) is polled and persisted to SQLite. Results are written
to a per-job directory under `results_dir`.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import yaml
from sqlmodel import Session, select

from hmm_core import load_topology, save_model
from hmm_core.fit import fit as core_fit
from hmm_core.topology import Topology, TopologyError
from hmm_studio.server.db import get_session
from hmm_studio.server.models import Dataset, FitJob, FitJobStatus

# Default thread pool size: half the CPUs, min 1
_DEFAULT_WORKERS = max(1, (os.cpu_count() or 2) // 2)


def _load_topology_from_yaml_str(yaml_str: str) -> Topology:
    """Parse a YAML string into a validated Topology. Raises TopologyError on invalid."""
    # Reuse load_topology via a temp file approach? No — we have a string.
    # Replicate the minimal parsing logic by using yaml.safe_load + Topology construction.
    from hmm_core.io import load_topology as _load_from_path
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tf:
        tf.write(yaml_str)
        tmp_path = tf.name
    try:
        return _load_from_path(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


class JobRunner:
    """Wraps a ThreadPoolExecutor with SQLite persistence."""

    def __init__(self, engine, results_dir: str | Path, max_workers: int = _DEFAULT_WORKERS):
        self._engine = engine
        self._results_dir = Path(results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def submit(self, topology_yaml: str, dataset_id: str, seed: int | None = None) -> str:
        """Create a FitJob row + schedule the fit. Returns job_id."""
        with get_session(self._engine) as session:
            job = FitJob(
                topology=topology_yaml,
                dataset_id=dataset_id,
                seed=seed,
                status=FitJobStatus.QUEUED,
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

        future = self._executor.submit(self._run, job_id)
        with self._lock:
            self._futures[job_id] = future
        return job_id

    def get_status(self, job_id: str) -> dict:
        """Return the latest persisted status of a job as a dict."""
        with get_session(self._engine) as session:
            job = session.get(FitJob, job_id)
            if job is None:
                raise KeyError(f"unknown job_id {job_id!r}")
            return {
                "id": job.id,
                "status": job.status.value,
                "progress": json.loads(job.progress) if job.progress else [],
                "log_likelihood": _maybe_float(job, "log_likelihood"),
                "bic": _maybe_float(job, "bic"),
                "aic": _maybe_float(job, "aic"),
                "n_iter_actual": _maybe_int(job, "n_iter_actual"),
                "converged": _maybe_bool(job, "converged"),
                "result_path": job.result_path,
                "error": job.error,
            }

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def _run(self, job_id: str) -> None:
        """Execute the fit for ``job_id``; updates the DB row throughout."""
        try:
            # Load job + dataset
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                if job is None:
                    return
                dataset = session.get(Dataset, job.dataset_id)
                if dataset is None:
                    job.status = FitJobStatus.FAILED
                    job.error = f"dataset {job.dataset_id} not found"
                    job.ended_at = datetime.utcnow()
                    session.add(job)
                    session.commit()
                    return
                topology_yaml = job.topology
                seed = job.seed
                dataset_path = dataset.path

            # Validate topology
            try:
                topology = _load_topology_from_yaml_str(topology_yaml)
            except (TopologyError, Exception) as exc:
                with get_session(self._engine) as session:
                    job = session.get(FitJob, job_id)
                    job.status = FitJobStatus.FAILED
                    job.error = f"invalid topology: {exc}"
                    job.ended_at = datetime.utcnow()
                    session.add(job)
                    session.commit()
                return

            # Load data
            df = pd.read_csv(dataset_path)
            X = df.to_numpy(dtype=float) if topology.emission.type != "multinomial" else df.to_numpy(dtype=int)

            # Mark running
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                job.status = FitJobStatus.RUNNING
                job.started_at = datetime.utcnow()
                session.add(job)
                session.commit()

            # Run fit + poll progress in a parallel thread
            result_container: dict = {}

            def _do_fit():
                try:
                    result_container["result"] = core_fit(topology, X, seed=seed)
                except Exception as exc:
                    result_container["error"] = exc

            fit_thread = threading.Thread(target=_do_fit)
            fit_thread.start()
            # Poll progress every 200ms while the fit runs.
            while fit_thread.is_alive():
                fit_thread.join(timeout=0.2)
                # In this simple implementation, we can't read monitor_.history
                # mid-flight without access to the model object. The result_container
                # only gets the final result. We approximate progress by recording
                # a heartbeat tick; the real history is written after completion.
                # For now, leave progress empty until done. (B.2 streaming will
                # improve this; for B.1 the final progress is captured below.)

            if "error" in result_container:
                with get_session(self._engine) as session:
                    job = session.get(FitJob, job_id)
                    job.status = FitJobStatus.FAILED
                    job.error = str(result_container["error"])
                    job.ended_at = datetime.utcnow()
                    session.add(job)
                    session.commit()
                return

            result = result_container["result"]
            monitor = getattr(result.model, "monitor_", None)
            history = list(getattr(monitor, "history", [])) if monitor is not None else []

            # Save the result bundle.
            result_dir = self._results_dir / job_id
            result_dir.mkdir(parents=True, exist_ok=True)
            save_model(result, result_dir)

            # Persist final status.
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                job.status = FitJobStatus.DONE
                job.progress = json.dumps([float(x) for x in history])
                job.result_path = str(result_dir)
                job.ended_at = datetime.utcnow()
                # Store result metadata in progress for now; B.2 will properly expose.
                session.add(job)
                session.commit()

        except Exception as exc:
            # Catch-all: persist failure
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                if job is not None:
                    job.status = FitJobStatus.FAILED
                    job.error = f"unexpected error: {exc}"
                    job.ended_at = datetime.utcnow()
                    session.add(job)
                    session.commit()


def _maybe_float(job: FitJob, key: str) -> float | None:
    """Read the model summary from result_path/summary.json if available."""
    if not job.result_path:
        return None
    summary_path = Path(job.result_path) / "summary.json"
    if not summary_path.exists():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        if key in ("log_likelihood", "bic", "aic"):
            return float(data["fit"][key])
    except Exception:
        return None
    return None


def _maybe_int(job: FitJob, key: str) -> int | None:
    if not job.result_path:
        return None
    summary_path = Path(job.result_path) / "summary.json"
    if not summary_path.exists():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return int(data["fit"][key])
    except Exception:
        return None


def _maybe_bool(job: FitJob, key: str) -> bool | None:
    if not job.result_path:
        return None
    summary_path = Path(job.result_path) / "summary.json"
    if not summary_path.exists():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return bool(data["fit"][key])
    except Exception:
        return None
```

- [ ] **Step 4.4: Run tests — confirm pass**

```powershell
pytest tests/studio/test_jobs.py -v
```

Expected: 4 passes. Each test runs ~5-15 seconds (real EM fit).

- [ ] **Step 4.5: Commit**

```bash
git add src/hmm_studio/server/jobs.py tests/studio/test_jobs.py
git commit -m "feat(studio): JobRunner with ThreadPoolExecutor + SQLite persistence"
```

---

## Task B.1.5: FastAPI app + REST endpoints

**Files:**
- Create: `src/hmm_studio/server/app.py`
- Create: `tests/studio/test_endpoints.py`

- [ ] **Step 5.1: Write failing tests**

`tests/studio/test_endpoints.py`:

```python
"""Tests for FastAPI REST endpoints."""

from __future__ import annotations

import io
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from hmm_studio.server.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HMM_STUDIO_DB_PATH", str(tmp_path / "studio.db"))
    monkeypatch.setenv("HMM_STUDIO_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("HMM_STUDIO_UPLOADS_DIR", str(tmp_path / "uploads"))
    app = create_app()
    return TestClient(app)


VALID_TOPOLOGY = """
name: t
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 20, tol: 1.0e-4}
"""


def _make_csv_bytes(seed: int = 42, n: int = 300) -> bytes:
    rng = np.random.default_rng(seed)
    X = np.vstack([
        rng.normal(loc=-2.0, scale=0.3, size=(n // 3, 2)),
        rng.normal(loc=0.0, scale=0.3, size=(n // 3, 2)),
        rng.normal(loc=2.0, scale=0.3, size=(n // 3, 2)),
    ])
    buf = io.StringIO()
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_topology_validate_ok(client):
    r = client.post("/api/topology/validate", json={"yaml_content": VALID_TOPOLOGY})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["error"] is None


def test_topology_validate_bad(client):
    r = client.post("/api/topology/validate", json={"yaml_content": "not: valid"})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["error"]


def test_data_upload_and_preview(client):
    csv_bytes = _make_csv_bytes()
    r = client.post(
        "/api/data/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
    )
    assert r.status_code == 200, r.text
    preview = r.json()
    assert preview["id"]
    assert preview["filename"] == "data.csv"
    assert preview["n_rows"] == 300
    assert preview["n_cols"] == 2
    assert "f0" in preview["columns"]
    assert len(preview["head"]) > 0


def test_fit_start_and_status(client):
    # Upload
    csv_bytes = _make_csv_bytes()
    r = client.post(
        "/api/data/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
    )
    dataset_id = r.json()["id"]

    # Start fit
    r = client.post(
        "/api/fit/start",
        json={
            "topology_yaml": VALID_TOPOLOGY,
            "dataset_id": dataset_id,
            "seed": 42,
        },
    )
    assert r.status_code == 200
    job_id = r.json()["id"]

    # Poll status
    for _ in range(60):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)

    final = r.json()
    assert final["status"] == "done", final
    assert final["log_likelihood"] is not None
    assert final["bic"] is not None


def test_fit_invalid_topology_fails(client):
    csv_bytes = _make_csv_bytes()
    r = client.post(
        "/api/data/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
    )
    dataset_id = r.json()["id"]
    r = client.post(
        "/api/fit/start",
        json={"topology_yaml": "not: valid", "dataset_id": dataset_id},
    )
    assert r.status_code == 200
    job_id = r.json()["id"]
    for _ in range(20):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    assert r.json()["status"] == "failed"


def test_unknown_dataset_returns_404(client):
    r = client.get("/api/data/nonexistent-id/preview")
    assert r.status_code == 404
```

- [ ] **Step 5.2: Run — expect failures**

```powershell
pytest tests/studio/test_endpoints.py -v
```

Expected: 8 ImportError failures (or similar).

- [ ] **Step 5.3: Implement `src/hmm_studio/server/app.py`**

```python
"""FastAPI app factory: routes + lifespan + dependency wiring."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from hmm_studio.server.db import create_db_engine, get_session
from hmm_studio.server.jobs import JobRunner, _load_topology_from_yaml_str
from hmm_studio.server.models import Dataset, FitJob
from hmm_studio.server.schemas import (
    DatasetPreview,
    FitJobCreate,
    FitJobResult,
    TopologyValidateRequest,
    TopologyValidateResponse,
)


# Defaults: ~/.hmm-studio/, overridable via env vars.
def _default_root() -> Path:
    home = Path.home() / ".hmm-studio"
    return home


def _resolve_paths():
    root = _default_root()
    db_path = Path(os.environ.get("HMM_STUDIO_DB_PATH", str(root / "studio.db")))
    results_dir = Path(os.environ.get("HMM_STUDIO_RESULTS_DIR", str(root / "results")))
    uploads_dir = Path(os.environ.get("HMM_STUDIO_UPLOADS_DIR", str(root / "uploads")))
    return db_path, results_dir, uploads_dir


def create_app() -> FastAPI:
    """Create a FastAPI app with all routes wired."""
    db_path, results_dir, uploads_dir = _resolve_paths()
    results_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(db_path)
    runner = JobRunner(engine=engine, results_dir=results_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        runner.shutdown(wait=False)

    app = FastAPI(title="hmm-studio", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # ----- Topology -----
    @app.post("/api/topology/validate", response_model=TopologyValidateResponse)
    def validate_topology(req: TopologyValidateRequest):
        try:
            topo = _load_topology_from_yaml_str(req.yaml_content)
        except Exception as exc:
            return TopologyValidateResponse(valid=False, error=str(exc), summary=None)
        return TopologyValidateResponse(
            valid=True,
            error=None,
            summary=f"valid: {topo.name} (n_states={topo.n_states}, emission={topo.emission.type})",
        )

    # ----- Datasets -----
    @app.post("/api/data/upload", response_model=DatasetPreview)
    def upload_dataset(file: UploadFile = File(...)):
        contents = file.file.read()
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="file too large (max 50MB)")
        dataset_id = str(uuid.uuid4())
        path = uploads_dir / f"{dataset_id}.csv"
        path.write_bytes(contents)
        # Parse to compute metadata
        df = pd.read_csv(path)
        ds = Dataset(
            id=dataset_id,
            filename=file.filename or "uploaded.csv",
            n_rows=len(df),
            n_cols=len(df.columns),
            dtypes=json.dumps({c: str(df[c].dtype) for c in df.columns}),
            path=str(path),
        )
        with get_session(engine) as session:
            session.add(ds)
            session.commit()
        return DatasetPreview(
            id=ds.id,
            filename=ds.filename,
            n_rows=ds.n_rows,
            n_cols=ds.n_cols,
            columns=list(df.columns),
            dtypes={c: str(df[c].dtype) for c in df.columns},
            head=df.head(10).to_dict(orient="records"),
        )

    @app.get("/api/data/{dataset_id}/preview", response_model=DatasetPreview)
    def get_dataset_preview(dataset_id: str):
        with get_session(engine) as session:
            ds = session.get(Dataset, dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
            df = pd.read_csv(ds.path)
            return DatasetPreview(
                id=ds.id,
                filename=ds.filename,
                n_rows=ds.n_rows,
                n_cols=ds.n_cols,
                columns=list(df.columns),
                dtypes={c: str(df[c].dtype) for c in df.columns},
                head=df.head(10).to_dict(orient="records"),
            )

    # ----- Fit jobs -----
    @app.post("/api/fit/start", response_model=FitJobResult)
    def start_fit(req: FitJobCreate):
        # Validate dataset exists
        with get_session(engine) as session:
            ds = session.get(Dataset, req.dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
        job_id = runner.submit(
            topology_yaml=req.topology_yaml,
            dataset_id=req.dataset_id,
            seed=req.seed,
        )
        status = runner.get_status(job_id)
        return FitJobResult(
            id=status["id"],
            status=status["status"],
            log_likelihood=status.get("log_likelihood"),
            bic=status.get("bic"),
            aic=status.get("aic"),
            n_iter_actual=status.get("n_iter_actual"),
            converged=status.get("converged"),
            result_path=status.get("result_path"),
            error=status.get("error"),
        )

    @app.get("/api/fit/{job_id}", response_model=FitJobResult)
    def get_fit_status(job_id: str):
        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        return FitJobResult(
            id=status["id"],
            status=status["status"],
            log_likelihood=status.get("log_likelihood"),
            bic=status.get("bic"),
            aic=status.get("aic"),
            n_iter_actual=status.get("n_iter_actual"),
            converged=status.get("converged"),
            result_path=status.get("result_path"),
            error=status.get("error"),
        )

    return app
```

- [ ] **Step 5.4: Run tests — confirm pass**

```powershell
pytest tests/studio/test_endpoints.py -v
```

Expected: 7-8 passes. Some tests use real fits (~10-15s each).

- [ ] **Step 5.5: Full suite**

```powershell
pytest -q
```

Expected: ~85 total passes (66 hmm-core + new studio tests). No regressions.

- [ ] **Step 5.6: Commit**

```bash
git add src/hmm_studio/server/app.py tests/studio/test_endpoints.py
git commit -m "feat(studio): FastAPI app with topology/data/fit endpoints"
```

---

## Task B.1.6: CLI entry point

**Files:**
- Create: `src/hmm_studio/cli.py`
- Create: `tests/studio/test_cli.py`

- [ ] **Step 6.1: Implement `src/hmm_studio/cli.py`**

```python
"""hmm-studio CLI: `hmm-studio serve` to launch the web UI."""

from __future__ import annotations

import typer
import uvicorn

app = typer.Typer(help="hmm-studio: web UI for hmm-core.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host. Default localhost-only."),
    port: int = typer.Option(8000, help="Port to bind."),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev only)."),
) -> None:
    """Launch the hmm-studio web server."""
    if reload:
        # uvicorn reload only works with an import string, not an app instance.
        uvicorn.run(
            "hmm_studio.server.app:create_app",
            host=host,
            port=port,
            reload=True,
            factory=True,
        )
    else:
        from hmm_studio.server.app import create_app
        uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    app()
```

- [ ] **Step 6.2: Smoke test — verify the CLI registers and `--help` works**

```powershell
hmm-studio --help
```

Expected: typer help showing the `serve` subcommand.

```powershell
hmm-studio serve --help
```

Expected: shows host/port/reload flags.

- [ ] **Step 6.3: Add a tiny CLI test (no actual server launch)**

`tests/studio/test_cli.py`:

```python
"""Smoke tests for the hmm-studio CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from hmm_studio.cli import app


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.stdout.lower()


def test_cli_serve_help():
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "host" in result.stdout.lower()
    assert "port" in result.stdout.lower()
```

- [ ] **Step 6.4: Run**

```powershell
pytest tests/studio/test_cli.py -v
```

Expected: 2 passes.

- [ ] **Step 6.5: Commit**

```bash
git add src/hmm_studio/cli.py tests/studio/test_cli.py
git commit -m "feat(studio): hmm-studio serve CLI entry point"
```

---

## Task B.1.7: Manual smoke test

- [ ] **Step 7.1: Start the server manually**

```powershell
hmm-studio serve --port 8765
```

The server should start at http://127.0.0.1:8765.

In another shell, hit the health endpoint:

```powershell
curl http://127.0.0.1:8765/health
```

Expected: `{"status":"ok"}`.

Try the topology validation:

```powershell
curl -X POST http://127.0.0.1:8765/api/topology/validate -H "Content-Type: application/json" -d '{\"yaml_content\":\"name: t\\nn_states: 2\\nstate_names: [a, b]\\nemission: {type: gaussian, covariance_type: full, n_features: 1}\\nstartprob: uniform\\ninit: {strategy: uniform, seed: 0}\\nfit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-4}\"}'
```

Expected: `{"valid":true,"error":null,"summary":"valid: t (n_states=2, emission=gaussian)"}`.

Open `http://127.0.0.1:8765/docs` in a browser — you should see the FastAPI Swagger UI listing all endpoints.

**Stop the server** (Ctrl+C).

---

## Task B.1.8: Quality gates + final commit

- [ ] **Step 8.1: Ruff + black + pytest**

```powershell
ruff check src/ tests/
black --check src/ tests/
pytest -q
```

All must pass. If ruff or black flag issues, fix with `--fix` (ruff) or `black src/ tests/`. Commit any auto-fix separately if it changes files outside this task's scope.

- [ ] **Step 8.2: Confirm test count**

`pytest -q` should show approximately 85+ tests (66 hmm-core + ~20 studio).

- [ ] **Step 8.3: Update README to mention B.1 ship**

Append to `README.md` after the existing sections (don't replace anything):

```markdown
## Web UI (B.1 backend skeleton)

`hmm-studio` (sub-project B) is in progress. The backend skeleton ships with:

- FastAPI app with topology validation, dataset upload, and fit job orchestration
- SQLite persistence (jobs survive restarts)
- ThreadPoolExecutor for parallel fits

Install + launch:

\`\`\`bash
pip install -e ".[web,dev]"
hmm-studio serve
# Open http://127.0.0.1:8000/docs for the Swagger UI
\`\`\`

Frontend (B.3+) is planned but not yet implemented. See [docs/roadmap.md](docs/roadmap.md).
```

(Use real backticks in the actual file.)

- [ ] **Step 8.4: Commit**

```bash
git add README.md
git commit -m "docs: README mentions B.1 backend ship + serve command"
```

---

## Done criteria

After completing all 8 tasks, the following must hold:

- `hmm-studio serve` launches the FastAPI app and serves `/health`, `/api/topology/validate`, `/api/data/upload`, `/api/fit/start`, `/api/fit/{job_id}`.
- SQLite DB at `~/.hmm-studio/studio.db` (or overridable via env vars).
- Fit jobs run in a ThreadPoolExecutor and persist their result to `~/.hmm-studio/results/{job_id}/`.
- All studio tests pass (`pytest tests/studio/ -v`).
- Full suite: 85+ tests, all green.
- Code passes ruff + black checks.
- Swagger UI accessible at `/docs`.

## What's NOT in B.1 (scope of B.2+)

- WebSocket for streaming Baum-Welch progress mid-fit (B.2)
- Decode endpoint (covered in T9 of hmm-core CLI — not yet wrapped in REST)
- Cancel job endpoint
- Frontend (B.3, B.4, B.5, B.6)
- Static file serving (B.8)

These are tracked in `docs/specs/2026-05-21-hmm-studio-web-design.md` for future sessions.
