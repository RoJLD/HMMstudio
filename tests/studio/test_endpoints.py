"""Tests for FastAPI REST endpoints."""

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
    csv_bytes = _make_csv_bytes()
    r = client.post(
        "/api/data/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
    )
    dataset_id = r.json()["id"]

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


def test_websocket_progress_streams_and_closes(client):
    """Open a WebSocket on a fit job; receive updates until terminal."""
    csv_bytes = _make_csv_bytes()
    r = client.post(
        "/api/data/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
    )
    dataset_id = r.json()["id"]
    r = client.post(
        "/api/fit/start",
        json={"topology_yaml": VALID_TOPOLOGY, "dataset_id": dataset_id, "seed": 42},
    )
    job_id = r.json()["id"]

    with client.websocket_connect(f"/ws/fit/{job_id}") as ws:
        messages = []
        for _ in range(100):  # max 100 messages then bail
            try:
                msg = ws.receive_json()
            except Exception:
                break
            messages.append(msg)
            if msg["status"] in ("done", "failed"):
                break
        assert any(m["status"] == "done" for m in messages), [m["status"] for m in messages]
        # Final message should have progress with multiple entries (fit ran)
        final = messages[-1]
        assert len(final["progress"]) > 0


def test_websocket_unknown_job(client):
    """Connecting to an unknown job_id closes the WS cleanly with an error."""
    with client.websocket_connect("/ws/fit/nonexistent-id") as ws:
        msg = ws.receive_json()
        assert "error" in msg


def test_static_mount_serves_index_when_present(client, tmp_path, monkeypatch):
    """When src/hmm_studio/server/static/index.html exists, GET / serves it.

    This test creates a fake static dir to verify the wiring; the real build
    output is produced by scripts/build_frontend.py.
    """
    from pathlib import Path

    # Locate the server package dir
    import hmm_studio.server as server_pkg

    server_dir = Path(server_pkg.__file__).parent
    static_dir = server_dir / "static"
    assets_dir = static_dir / "assets"

    # Snapshot pre-test state to restore (other tests may rely on it)
    had_index = (static_dir / "index.html").exists()
    had_assets = assets_dir.exists()

    static_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    index_path = static_dir / "index.html"
    asset_path = assets_dir / "test.js"
    index_path.write_text("<!doctype html><html><body>test-spa</body></html>", encoding="utf-8")
    asset_path.write_text("console.log('test');", encoding="utf-8")

    try:
        # Build a fresh app picking up the new static dir.
        from hmm_studio.server.app import create_app

        app = create_app()
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            # GET / serves the SPA index.
            r = c.get("/")
            assert r.status_code == 200
            assert "test-spa" in r.text

            # GET /assets/test.js serves the asset.
            r = c.get("/assets/test.js")
            assert r.status_code == 200
            assert "console.log" in r.text

            # /health still works.
            r = c.get("/health")
            assert r.status_code == 200
            assert r.json() == {"status": "ok"}

            # Unknown frontend route falls back to index.html.
            r = c.get("/some/spa/route")
            assert r.status_code == 200
            assert "test-spa" in r.text
    finally:
        # Cleanup: only remove what we created.
        if not had_index and index_path.exists():
            index_path.unlink()
        if asset_path.exists():
            asset_path.unlink()
        if not had_assets and assets_dir.exists() and not list(assets_dir.iterdir()):
            assets_dir.rmdir()


def test_get_fit_transmat_done(client):
    """After a successful fit, /api/fit/{id}/transmat returns the matrix."""
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
    assert r.json()["status"] == "done"
    r = client.get(f"/api/fit/{job_id}/transmat")
    assert r.status_code == 200
    body = r.json()
    assert body["n_states"] == 3
    assert len(body["transmat"]) == 3
    assert len(body["transmat"][0]) == 3
    assert len(body["state_names"]) == 3


def test_get_fit_decoded_done(client):
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
    r = client.get(f"/api/fit/{job_id}/decoded")
    assert r.status_code == 200
    body = r.json()
    assert "viterbi" in body
    assert "posterior" in body
    assert body["n_total"] == 300


def test_get_fit_emissions_done(client):
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
    r = client.get(f"/api/fit/{job_id}/emissions")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "gaussian"
    assert len(body["means"]) == 3
