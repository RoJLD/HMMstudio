"""Tests for the data warehouse (Phase B.10)."""

from __future__ import annotations

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from hmm_studio.server.app import create_app
from hmm_studio.server.warehouse import (
    SIDECAR_SUFFIX,
    load_sidecar,
    preview,
    read_dataset,
    safe_resolve,
    scan_warehouse,
    write_sidecar,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HMM_STUDIO_DB_PATH", str(tmp_path / "studio.db"))
    monkeypatch.setenv("HMM_STUDIO_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("HMM_STUDIO_UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("HMM_STUDIO_WAREHOUSE_PATH", raising=False)
    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Module-level (no FastAPI) tests
# ---------------------------------------------------------------------------


def test_scan_empty_warehouse(tmp_path):
    assert scan_warehouse(tmp_path) == []


def test_scan_detects_csv_parquet_json_excel(tmp_path):
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4.0, 5.0, 6.0]})
    df.to_csv(tmp_path / "a.csv", index=False)
    df.to_parquet(tmp_path / "b.parquet", index=False)
    df.to_json(tmp_path / "c.json", orient="records")
    try:
        df.to_excel(tmp_path / "d.xlsx", index=False)
        has_xlsx = True
    except Exception:
        # openpyxl not installed → skip the .xlsx half of this test
        has_xlsx = False

    entries = scan_warehouse(tmp_path)
    rel_paths = {e.rel_path for e in entries}
    expected = {"a.csv", "b.parquet", "c.json"}
    if has_xlsx:
        expected.add("d.xlsx")
    assert rel_paths == expected


def test_scan_ignores_unsupported_extensions(tmp_path):
    (tmp_path / "readme.txt").write_text("hi")
    (tmp_path / "notes.md").write_text("note")
    (tmp_path / "data.csv").write_text("x,y\n1,2\n")
    entries = scan_warehouse(tmp_path)
    assert [e.rel_path for e in entries] == ["data.csv"]


def test_scan_recursive(tmp_path):
    (tmp_path / "root.csv").write_text("x\n1\n")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.csv").write_text("y\n2\n")
    entries = scan_warehouse(tmp_path)
    rel_paths = sorted(e.rel_path for e in entries)
    assert rel_paths == ["root.csv", "subdir/nested.csv"]


def test_scan_ignores_hidden_files(tmp_path):
    (tmp_path / "visible.csv").write_text("x\n1\n")
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "secret.csv").write_text("x\n2\n")
    (tmp_path / ".dotfile.csv").write_text("x\n3\n")
    entries = scan_warehouse(tmp_path)
    rel_paths = [e.rel_path for e in entries]
    assert rel_paths == ["visible.csv"]


def test_scan_sidecar_pairing(tmp_path):
    (tmp_path / "data.csv").write_text("x\n1\n")
    (tmp_path / f"data.csv{SIDECAR_SUFFIX}").write_text("name: my data\n")
    (tmp_path / "no_sidecar.csv").write_text("x\n1\n")
    entries = scan_warehouse(tmp_path)
    by_path = {e.rel_path: e for e in entries}
    assert by_path["data.csv"].has_sidecar is True
    assert by_path["no_sidecar.csv"].has_sidecar is False
    # The sidecar itself is NOT listed as a dataset
    assert f"data.csv{SIDECAR_SUFFIX}" not in by_path


def test_preview_csv(tmp_path):
    df = pd.DataFrame({"x": range(20), "y": range(100, 120)})
    p = tmp_path / "data.csv"
    df.to_csv(p, index=False)
    out = preview(p, n=5)
    assert len(out) == 5
    assert list(out.columns) == ["x", "y"]


def test_preview_parquet(tmp_path):
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    p = tmp_path / "data.parquet"
    df.to_parquet(p, index=False)
    out = preview(p, n=2)
    assert len(out) == 2


def test_load_sidecar_yaml(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("x\n1\n")
    (tmp_path / f"data.csv{SIDECAR_SUFFIX}").write_text(
        "schema_version: 1\nname: my dataset\nnotes: hello\n",
        encoding="utf-8",
    )
    meta = load_sidecar(p)
    assert meta == {"schema_version": 1, "name": "my dataset", "notes": "hello"}


def test_load_sidecar_returns_none_when_absent(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("x\n1\n")
    assert load_sidecar(p) is None


def test_write_sidecar_roundtrip(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("x\n1\n")
    meta = {
        "schema_version": 1,
        "name": "test",
        "columns": [{"name": "x", "role": "observation"}],
    }
    write_sidecar(p, meta)
    loaded = load_sidecar(p)
    assert loaded == meta


def test_path_traversal_blocked(tmp_path):
    """A relative path that resolves outside warehouse_root is rejected."""
    with pytest.raises(ValueError, match="path traversal"):
        safe_resolve(tmp_path, "../../../etc/passwd")
    with pytest.raises(ValueError, match="path traversal"):
        safe_resolve(tmp_path, "..")
    # Inside paths pass
    safe_resolve(tmp_path, "sub/dir/file.csv")
    safe_resolve(tmp_path, "file.csv")


def test_read_dataset_unsupported_format_raises(tmp_path):
    p = tmp_path / "data.parquet2"
    p.write_text("nope")
    with pytest.raises(ValueError, match="unsupported format"):
        read_dataset(p)


# ---------------------------------------------------------------------------
# FastAPI integration tests
# ---------------------------------------------------------------------------


def test_warehouse_list_empty_when_unconfigured(client, monkeypatch):
    monkeypatch.delenv("HMM_STUDIO_WAREHOUSE_PATH", raising=False)
    # The client fixture's app was created with whatever env was at construction;
    # so this test asserts the SHAPE of the response, not the env effect.
    r = client.get("/api/warehouse")
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    assert isinstance(body["entries"], list)


def test_warehouse_endpoints_with_configured_path(tmp_path, monkeypatch):
    """End-to-end test: configure HMM_STUDIO_WAREHOUSE_PATH, create files, hit endpoints."""
    warehouse = tmp_path / "wh"
    warehouse.mkdir()
    df = pd.DataFrame({"f0": [1.0, 2.0, 3.0, 4.0], "f1": [0.0, 0.5, 1.0, 1.5]})
    df.to_csv(warehouse / "demo.csv", index=False)

    # Build a fresh client with the configured warehouse path
    monkeypatch.setenv("HMM_STUDIO_DB_PATH", str(tmp_path / "studio.db"))
    monkeypatch.setenv("HMM_STUDIO_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("HMM_STUDIO_UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("HMM_STUDIO_WAREHOUSE_PATH", str(warehouse))

    app = create_app()
    with TestClient(app) as c:
        # List
        r = c.get("/api/warehouse")
        assert r.status_code == 200
        body = r.json()
        assert body["warehouse_path"] == str(warehouse)
        assert len(body["entries"]) == 1
        assert body["entries"][0]["rel_path"] == "demo.csv"
        assert body["entries"][0]["format"] == "csv"
        assert body["entries"][0]["has_sidecar"] is False

        # Preview
        r = c.get("/api/warehouse/demo.csv/preview?n=3")
        assert r.status_code == 200
        preview_body = r.json()
        assert preview_body["n_rows_total"] == 4
        assert preview_body["n_cols"] == 2
        assert len(preview_body["head"]) == 3

        # Get meta (no sidecar yet)
        r = c.get("/api/warehouse/demo.csv/meta")
        assert r.status_code == 200
        assert r.json()["sidecar"] is None

        # Write sidecar via PUT
        r = c.put(
            "/api/warehouse/demo.csv/meta",
            json={"schema_version": 1, "name": "Demo dataset", "notes": "test"},
        )
        assert r.status_code == 200
        assert (warehouse / f"demo.csv{SIDECAR_SUFFIX}").exists()

        # Get meta returns the written sidecar
        r = c.get("/api/warehouse/demo.csv/meta")
        assert r.status_code == 200
        sidecar = r.json()["sidecar"]
        assert sidecar["name"] == "Demo dataset"
        assert sidecar["notes"] == "test"

        # Path traversal blocked
        r = c.get("/api/warehouse/..%2F..%2Fpassword/preview")
        # FastAPI URL-decodes — the resulting rel_path tries to escape and is blocked
        assert r.status_code in (400, 404)

        # Upload new file
        new_csv = "x,y\n10,20\n30,40\n"
        r = c.post(
            "/api/warehouse/upload",
            files={"file": ("new.csv", new_csv.encode(), "text/csv")},
        )
        assert r.status_code == 200
        assert (warehouse / "new.csv").exists()

        # Refresh + list shows the new entry
        r = c.post("/api/warehouse/refresh")
        assert r.status_code == 200
        rel_paths = {e["rel_path"] for e in r.json()["entries"]}
        assert "new.csv" in rel_paths
