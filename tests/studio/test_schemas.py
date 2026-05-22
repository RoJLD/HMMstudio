"""Tests for Pydantic request/response schemas."""

from __future__ import annotations


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
    resp = TopologyValidateResponse(
        valid=False, error="missing required field: 'emission'", summary=None
    )
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
