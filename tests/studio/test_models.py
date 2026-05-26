"""Tests for SQLModel persistence: datasets, fit_jobs."""

from __future__ import annotations

import json
from datetime import datetime

from hmm_studio.server._time import utcnow
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
        ds = Dataset(filename="x.csv", n_rows=10, n_cols=2, dtypes="{}", path="/tmp/x.csv")
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
        ds = Dataset(filename="x.csv", n_rows=10, n_cols=2, dtypes="{}", path="/tmp/x.csv")
        session.add(ds)
        session.commit()
        session.refresh(ds)
        job = FitJob(topology="{}", dataset_id=ds.id, status=FitJobStatus.QUEUED)
        session.add(job)
        session.commit()
        session.refresh(job)

        # Transition to running
        job.status = FitJobStatus.RUNNING
        job.started_at = utcnow()
        session.add(job)
        session.commit()

        # Transition to done
        job.status = FitJobStatus.DONE
        job.ended_at = utcnow()
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
        from sqlmodel import select

        result = list(session.exec(select(Dataset)).all())
        assert result == []
