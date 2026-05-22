"""Pydantic schemas for FastAPI request/response bodies."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TopologyValidateRequest(BaseModel):
    yaml_content: str


class TopologyValidateResponse(BaseModel):
    valid: bool
    error: str | None = None
    summary: str | None = None


class DatasetPreview(BaseModel):
    id: str
    filename: str
    n_rows: int
    n_cols: int
    columns: list[str]
    dtypes: dict[str, str]
    head: list[dict[str, Any]]


class FitJobCreate(BaseModel):
    topology_yaml: str
    dataset_id: str
    seed: int | None = None
    covariate_names: list[str] | None = None  # NHMM: column names from dataset to use as Z


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
