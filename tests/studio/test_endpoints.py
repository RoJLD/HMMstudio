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
    # Context-manager form triggers FastAPI lifespan teardown, which calls
    # JobRunner.shutdown(). Without this, every test leaks a ThreadPoolExecutor
    # whose worker threads stay alive until the pytest process exits — fine in
    # isolation but a multiplier under I/O contention (e.g. Defender scanning).
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


def test_fit_nhmm_with_covariates(client):
    """A fit with covariate_names runs NHMM and exposes A_at endpoint."""
    import io
    import time
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    n = 300
    Z = rng.normal(size=n)
    X = np.zeros((n, 2))
    state = 0
    for t in range(n):
        X[t] = rng.normal(loc=state * 3, scale=0.5, size=2)
        state = (state + (1 if Z[t] > 0 else 0)) % 3
    df = pd.DataFrame({"f0": X[:, 0], "f1": X[:, 1], "z": Z})
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")

    r = client.post("/api/data/upload", files={"file": ("nhmm.csv", csv_bytes, "text/csv")})
    dataset_id = r.json()["id"]

    topology = """
name: nhmm_test
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 15, tol: 1.0e-4}
"""
    r = client.post(
        "/api/fit/start",
        json={
            "topology_yaml": topology,
            "dataset_id": dataset_id,
            "seed": 42,
            "covariate_names": ["z"],
        },
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]
    for _ in range(60):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    assert r.json()["status"] == "done", r.json()

    # NHMM info
    r = client.get(f"/api/fit/{job_id}/nhmm_info")
    assert r.status_code == 200
    info = r.json()
    assert info["is_nhmm"] is True
    assert info["T"] == 300
    assert info["covariate_names"] == ["z"]

    # A_at at t=0
    r = client.get(f"/api/fit/{job_id}/A_at?t=0")
    assert r.status_code == 200
    body = r.json()
    assert body["t"] == 0
    assert body["T"] == 300
    assert len(body["A"]) == 3

    # A_at out of range
    r = client.get(f"/api/fit/{job_id}/A_at?t=99999")
    assert r.status_code == 400


def test_get_nhmm_info_for_homogeneous_fit(client):
    """A regular (non-NHMM) fit returns is_nhmm=false."""
    import io
    import time
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    X = rng.normal(size=(100, 2))
    df = pd.DataFrame(X, columns=["f0", "f1"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload",
        files={"file": ("hom.csv", buf.getvalue().encode(), "text/csv")},
    )
    dataset_id = r.json()["id"]

    topology = """
name: hom
n_states: 2
state_names: [a, b]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 0}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-3}
"""
    r = client.post(
        "/api/fit/start",
        json={"topology_yaml": topology, "dataset_id": dataset_id},
    )
    job_id = r.json()["id"]
    for _ in range(60):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)

    r = client.get(f"/api/fit/{job_id}/nhmm_info")
    assert r.status_code == 200
    assert r.json()["is_nhmm"] is False


def test_kscan_runs_multiple_children_and_picks_best(client):
    """A K-scan launches K_max-K_min+1 children, all run, best is picked."""
    import io
    import time
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    X = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(100, 2)),
            rng.normal(loc=0.0, scale=0.3, size=(100, 2)),
            rng.normal(loc=2.0, scale=0.3, size=(100, 2)),
        ]
    )
    df = pd.DataFrame(X, columns=["f0", "f1"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload",
        files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")},
    )
    dataset_id = r.json()["id"]

    topology = """
name: scan_test
n_states: 2
state_names: [a, b]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 15, tol: 1.0e-3}
"""
    r = client.post(
        "/api/fit/scan/start",
        json={
            "topology_yaml": topology,
            "dataset_id": dataset_id,
            "k_min": 2,
            "k_max": 4,
            "seed": 42,
        },
    )
    assert r.status_code == 200, r.text
    parent_id = r.json()["parent_id"]

    # Poll until all children done
    scan = {}
    for _ in range(120):
        r = client.get(f"/api/fit/scan/{parent_id}")
        scan = r.json()
        if scan["overall_status"] in ("done", "failed"):
            break
        time.sleep(0.25)

    assert scan["overall_status"] == "done", scan
    assert len(scan["children"]) == 3
    assert {c["k"] for c in scan["children"]} == {2, 3, 4}
    # All children should be done
    done_children = [c for c in scan["children"] if c["status"] == "done"]
    assert len(done_children) == 3
    assert scan["best_k_by_bic"] in (2, 3, 4)


def test_kscan_invalid_range_returns_400(client):
    import io
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(np.zeros((10, 1)), columns=["f0"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload",
        files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")},
    )
    dataset_id = r.json()["id"]

    topology = """
name: bad_scan
n_states: 2
state_names: [a, b]
emission: {type: gaussian, covariance_type: full, n_features: 1}
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 5, tol: 1.0e-3}
"""
    r = client.post(
        "/api/fit/scan/start",
        json={
            "topology_yaml": topology,
            "dataset_id": dataset_id,
            "k_min": 5,
            "k_max": 2,  # invalid: max < min
        },
    )
    assert r.status_code == 400


def test_fit_with_lengths_succeeds(client):
    """A multi-sequence fit with explicit lengths runs and returns done."""
    import io
    import time
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    X = np.vstack(
        [
            rng.normal(loc=-2.0, scale=0.3, size=(100, 2)),
            rng.normal(loc=0.0, scale=0.3, size=(100, 2)),
            rng.normal(loc=2.0, scale=0.3, size=(100, 2)),
        ]
    )
    df = pd.DataFrame(X, columns=["f0", "f1"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload",
        files={"file": ("multi.csv", buf.getvalue().encode(), "text/csv")},
    )
    dataset_id = r.json()["id"]

    topology = """
name: multi_seq
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 15, tol: 1.0e-3}
"""
    r = client.post(
        "/api/fit/start",
        json={
            "topology_yaml": topology,
            "dataset_id": dataset_id,
            "seed": 42,
            "lengths": [100, 100, 100],
        },
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]
    for _ in range(60):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    assert r.json()["status"] == "done", r.json()


def test_fit_with_invalid_lengths_sum_fails(client):
    """If sum(lengths) != n_rows, the fit fails with a clear error."""
    import io
    import time
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    X = rng.normal(size=(100, 2))
    df = pd.DataFrame(X, columns=["f0", "f1"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload",
        files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")},
    )
    dataset_id = r.json()["id"]

    topology = """
name: bad_lengths
n_states: 2
state_names: [a, b]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 5, tol: 1.0e-3}
"""
    r = client.post(
        "/api/fit/start",
        json={
            "topology_yaml": topology,
            "dataset_id": dataset_id,
            "lengths": [50, 30],  # sum 80 != 100
        },
    )
    assert r.status_code == 200  # job is queued OK
    job_id = r.json()["id"]
    for _ in range(30):
        r = client.get(f"/api/fit/{job_id}")
        if r.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    final = r.json()
    assert final["status"] == "failed"
    assert "lengths" in (final["error"] or "").lower()


def test_annotations_upload_and_list(client):
    import io
    import numpy as np
    import pandas as pd

    # Upload a dataset of 100 rows
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(100, 2)), columns=["f0", "f1"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload", files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")}
    )
    dataset_id = r.json()["id"]

    # Upload annotations
    ann_csv = "t,label,color\n10,first,blue\n50,middle,red\n90,last,green\n"
    r = client.post(
        f"/api/data/{dataset_id}/annotations/upload",
        files={"file": ("ann.csv", ann_csv.encode(), "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dataset_id"] == dataset_id
    assert len(body["annotations"]) == 3
    assert body["annotations"][0]["t"] == 10
    assert body["annotations"][0]["label"] == "first"

    # List
    r = client.get(f"/api/data/{dataset_id}/annotations")
    assert r.status_code == 200
    listed = r.json()
    assert len(listed["annotations"]) == 3
    # Should be sorted by t
    ts = [a["t"] for a in listed["annotations"]]
    assert ts == sorted(ts)


def test_annotations_upload_rejects_out_of_range(client):
    import io
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(np.zeros((10, 1)), columns=["f0"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload", files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")}
    )
    dataset_id = r.json()["id"]

    ann_csv = "t,label\n5,ok\n999,out_of_range\n"
    r = client.post(
        f"/api/data/{dataset_id}/annotations/upload",
        files={"file": ("ann.csv", ann_csv.encode(), "text/csv")},
    )
    assert r.status_code == 400
    assert "t values" in r.json()["detail"]


def test_annotations_upload_rejects_missing_columns(client):
    import io
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(np.zeros((10, 1)), columns=["f0"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload", files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")}
    )
    dataset_id = r.json()["id"]

    ann_csv = "foo,bar\n1,2\n"
    r = client.post(
        f"/api/data/{dataset_id}/annotations/upload",
        files={"file": ("ann.csv", ann_csv.encode(), "text/csv")},
    )
    assert r.status_code == 400
    assert "label" in r.json()["detail"]


def test_annotations_replace_on_re_upload(client):
    import io
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(np.zeros((100, 1)), columns=["f0"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload", files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")}
    )
    dataset_id = r.json()["id"]

    ann1 = "t,label\n10,a\n20,b\n"
    client.post(
        f"/api/data/{dataset_id}/annotations/upload",
        files={"file": ("ann.csv", ann1.encode(), "text/csv")},
    )
    ann2 = "t,label\n50,c\n"
    client.post(
        f"/api/data/{dataset_id}/annotations/upload",
        files={"file": ("ann.csv", ann2.encode(), "text/csv")},
    )
    r = client.get(f"/api/data/{dataset_id}/annotations")
    assert len(r.json()["annotations"]) == 1
    assert r.json()["annotations"][0]["label"] == "c"


def test_delete_annotation(client):
    import io
    import numpy as np
    import pandas as pd

    df = pd.DataFrame(np.zeros((100, 1)), columns=["f0"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    r = client.post(
        "/api/data/upload", files={"file": ("d.csv", buf.getvalue().encode(), "text/csv")}
    )
    dataset_id = r.json()["id"]

    ann = "t,label\n10,a\n20,b\n"
    r = client.post(
        f"/api/data/{dataset_id}/annotations/upload",
        files={"file": ("ann.csv", ann.encode(), "text/csv")},
    )
    ann_id = r.json()["annotations"][0]["id"]

    r = client.delete(f"/api/data/{dataset_id}/annotations/{ann_id}")
    assert r.status_code == 200

    r = client.get(f"/api/data/{dataset_id}/annotations")
    assert len(r.json()["annotations"]) == 1
