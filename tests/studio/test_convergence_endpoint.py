"""GET /api/fit/{id}/convergence returns the persisted EM trace."""

from __future__ import annotations

import io
import time

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
    with TestClient(app) as c:
        yield c


VALID_TOPOLOGY = """
name: t
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 20, tol: 1.0e-4}
"""


def _make_csv_bytes(seed=42, n=300):
    rng = np.random.default_rng(seed)
    X = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(n // 3, 2)),
            rng.normal(loc=0.0, scale=0.3, size=(n // 3, 2)),
            rng.normal(loc=2.0, scale=0.3, size=(n // 3, 2)),
        ]
    )
    buf = io.StringIO()
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def test_convergence_endpoint_returns_trace(client):
    csv_bytes = _make_csv_bytes()
    r = client.post("/api/data/upload", files={"file": ("d.csv", csv_bytes, "text/csv")})
    dataset_id = r.json()["id"]
    r = client.post(
        "/api/fit/start",
        json={"topology_yaml": VALID_TOPOLOGY, "dataset_id": dataset_id, "seed": 42},
    )
    job_id = r.json()["id"]
    for _ in range(60):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    assert r.json()["status"] == "done", r.json()

    resp = client.get(f"/api/fit/{job_id}/convergence")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["convergence_history"], list)
    assert len(body["convergence_history"]) >= 2
    assert "converged" in body and "n_iter_actual" in body
