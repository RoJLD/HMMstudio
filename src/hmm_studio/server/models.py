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
    dtypes: str = ""
    path: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FitJob(SQLModel, table=True):
    """A fit job: topology + dataset + execution metadata."""

    id: str = Field(default_factory=_uuid_str, primary_key=True)
    topology: str = ""
    dataset_id: str = Field(foreign_key="dataset.id")
    seed: int | None = None
    status: FitJobStatus = Field(default=FitJobStatus.QUEUED)
    progress: str = ""
    result_path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
