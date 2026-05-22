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
    lengths: list[int] | None = None  # multi-sequence boundaries


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
    dataset_id: str | None = None  # for annotation lookups


class FitJobScanCreate(BaseModel):
    """Launch a K-scan: one child fit per K in [k_min, k_max]."""

    topology_yaml: str
    dataset_id: str
    k_min: int
    k_max: int
    seed: int | None = None
    covariate_names: list[str] | None = None  # NHMM still supported per child
    lengths: list[int] | None = None  # multi-sequence boundaries


class ScanChildStatus(BaseModel):
    """One child K's status in a scan."""

    job_id: str
    k: int
    status: str
    log_likelihood: float | None = None
    bic: float | None = None
    aic: float | None = None
    converged: bool | None = None
    n_iter_actual: int | None = None
    error: str | None = None


class ScanResult(BaseModel):
    parent_id: str
    k_min: int
    k_max: int
    overall_status: str  # "queued" | "running" | "done" | "failed"
    children: list[ScanChildStatus]
    best_k_by_bic: int | None = None
    best_k_by_aic: int | None = None


class AnnotationOut(BaseModel):
    id: str
    dataset_id: str
    t: int
    label: str
    color: str | None = None


class AnnotationsResponse(BaseModel):
    dataset_id: str
    annotations: list[AnnotationOut]
