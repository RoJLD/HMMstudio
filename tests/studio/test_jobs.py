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
from hmm_studio.server.models import Dataset

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

    rng = np.random.default_rng(42)
    X = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(100, 2)),
            rng.normal(loc=0.0, scale=0.3, size=(100, 2)),
            rng.normal(loc=2.0, scale=0.3, size=(100, 2)),
        ]
    )
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(csv_path, index=False)

    with get_session(engine) as s:
        ds = Dataset(
            filename="data.csv",
            n_rows=300,
            n_cols=2,
            dtypes=json.dumps({"f0": "float64", "f1": "float64"}),
            path=str(csv_path),
        )
        s.add(ds)
        s.commit()
        s.refresh(ds)
        dataset_id = ds.id

    return {"engine": engine, "results_dir": results_dir, "dataset_id": dataset_id}


def _wait_for_status(runner, job_id, terminal=("done", "failed"), timeout_s=30):
    for _ in range(int(timeout_s / 0.1)):
        status = runner.get_status(job_id)
        if status["status"] in terminal:
            return status
        time.sleep(0.1)
    return runner.get_status(job_id)


def test_submit_runs_and_finishes(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    try:
        job_id = runner.submit(
            topology_yaml=VALID_TOPOLOGY_YAML,
            dataset_id=setup_env["dataset_id"],
            seed=42,
        )
        final = _wait_for_status(runner, job_id)
        assert final["status"] == "done", final
        assert final["log_likelihood"] is not None
        assert final["bic"] is not None
    finally:
        runner.shutdown()


def test_submit_invalid_topology_fails(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    try:
        job_id = runner.submit(
            topology_yaml="not: a valid: topology",
            dataset_id=setup_env["dataset_id"],
            seed=42,
        )
        final = _wait_for_status(runner, job_id, timeout_s=10)
        assert final["status"] == "failed", final
        assert final["error"] is not None
    finally:
        runner.shutdown()


def test_progress_updates_after_fit(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    try:
        job_id = runner.submit(
            topology_yaml=VALID_TOPOLOGY_YAML,
            dataset_id=setup_env["dataset_id"],
            seed=42,
        )
        final = _wait_for_status(runner, job_id)
        assert final["status"] == "done"
        assert len(final["progress"]) > 0
        progress = final["progress"]
        # log-likelihood should improve overall
        assert progress[-1] >= progress[0] - 1e-3
    finally:
        runner.shutdown()


def test_result_path_contains_artifacts(setup_env):
    runner = JobRunner(engine=setup_env["engine"], results_dir=setup_env["results_dir"])
    try:
        job_id = runner.submit(
            topology_yaml=VALID_TOPOLOGY_YAML,
            dataset_id=setup_env["dataset_id"],
            seed=42,
        )
        final = _wait_for_status(runner, job_id)
        result_dir = Path(final["result_path"])
        assert (result_dir / "model.pkl").exists()
        assert (result_dir / "summary.json").exists()
        assert (result_dir / "fit_log.txt").exists()
    finally:
        runner.shutdown()


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
