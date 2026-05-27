"""SQLModel database schema for hmm-studio backend."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from hmm_studio.server._time import utcnow


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
    created_at: datetime = Field(default_factory=utcnow)


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
    created_at: datetime = Field(default_factory=utcnow)
    covariate_names: str = ""  # JSON list[str] of column names used as NHMM covariates
    lengths: str = ""  # JSON list[int], empty = single sequence
    parent_id: str | None = Field(default=None)  # if set, this is a child of a scan job
    k_override: int | None = None  # if set, this child overrides topology.n_states
    emission_override: str | None = Field(default=None)  # compare: per-child emission family
    n_mix_override: int | None = Field(default=None)  # compare: GMM mixture count (gmm children only)


class Annotation(SQLModel, table=True):
    """External event annotation attached to a Dataset.

    `t` is the observation index in [0, dataset.n_rows). `label` is a short
    free-text description. `color` is an optional CSS color hint for the UI.
    """

    id: str = Field(default_factory=_uuid_str, primary_key=True)
    dataset_id: str = Field(foreign_key="dataset.id")
    t: int
    label: str
    color: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class SettingsRow(SQLModel, table=True):
    """Single-row user settings table.

    Always use ``id='global'`` as the only key. The DB stores user-editable
    overrides for values that otherwise come from env vars / defaults.
    """

    id: str = Field(default="global", primary_key=True)
    warehouse_path: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)
