"""Tests for /api/settings (Phase B.10 §7).

These cover the DB > env > unset precedence, path validation, and the
"settings update takes effect without server restart" requirement.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from hmm_studio.server.app import create_app


@pytest.fixture
def env_paths(tmp_path, monkeypatch):
    """Configure ephemeral DB / results / uploads. Warehouse env is left unset."""
    monkeypatch.setenv("HMM_STUDIO_DB_PATH", str(tmp_path / "studio.db"))
    monkeypatch.setenv("HMM_STUDIO_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("HMM_STUDIO_UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("HMM_STUDIO_WAREHOUSE_PATH", raising=False)
    return tmp_path


def _mk_client() -> TestClient:
    return TestClient(create_app())


def test_get_settings_initial_empty_db_returns_env_value(env_paths, monkeypatch):
    """DB empty + env var set -> resolved = env, source = 'env'."""
    wh = env_paths / "wh"
    wh.mkdir()
    monkeypatch.setenv("HMM_STUDIO_WAREHOUSE_PATH", str(wh))

    with _mk_client() as c:
        r = c.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        assert body["warehouse_path"] == str(wh.resolve())
        assert body["warehouse_path_source"] == "env"
        assert body["warehouse_path_env"] == str(wh)
        assert body["updated_at"] is None  # no DB row written yet


def test_get_settings_initial_empty_db_no_env_returns_none(env_paths):
    """DB empty + no env var -> resolved = None, source = 'unset'."""
    with _mk_client() as c:
        r = c.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        assert body["warehouse_path"] is None
        assert body["warehouse_path_source"] == "unset"
        assert body["warehouse_path_env"] is None
        assert body["updated_at"] is None


def test_put_settings_warehouse_path_valid_dir_persists(env_paths):
    """PUT a valid directory -> 200; subsequent GET returns it with source='db'."""
    wh = env_paths / "wh"
    wh.mkdir()

    with _mk_client() as c:
        r = c.put("/api/settings", json={"warehouse_path": str(wh)})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["warehouse_path"] == str(wh.resolve())
        assert body["warehouse_path_source"] == "db"
        assert body["updated_at"] is not None

        r2 = c.get("/api/settings")
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["warehouse_path"] == str(wh.resolve())
        assert body2["warehouse_path_source"] == "db"


def test_put_settings_warehouse_path_invalid_returns_400(env_paths):
    """Non-existent path -> 400; settings remain unchanged."""
    missing = env_paths / "does_not_exist_xyz"

    with _mk_client() as c:
        r = c.put("/api/settings", json={"warehouse_path": str(missing)})
        assert r.status_code == 400
        assert "does not exist" in r.json()["detail"]

        # Settings still unset
        r2 = c.get("/api/settings")
        assert r2.json()["warehouse_path_source"] == "unset"


def test_put_settings_warehouse_path_file_not_dir_returns_400(env_paths):
    """A file path (not a directory) -> 400."""
    f = env_paths / "not_a_dir.txt"
    f.write_text("hi")

    with _mk_client() as c:
        r = c.put("/api/settings", json={"warehouse_path": str(f)})
        assert r.status_code == 400
        assert "not a directory" in r.json()["detail"]


def test_put_settings_empty_string_clears_db_override(env_paths, monkeypatch):
    """Set then clear: source falls back to env (or 'unset' if env empty)."""
    wh = env_paths / "wh"
    wh.mkdir()
    env_wh = env_paths / "env_wh"
    env_wh.mkdir()
    monkeypatch.setenv("HMM_STUDIO_WAREHOUSE_PATH", str(env_wh))

    with _mk_client() as c:
        # Set DB override
        r = c.put("/api/settings", json={"warehouse_path": str(wh)})
        assert r.status_code == 200
        assert r.json()["warehouse_path_source"] == "db"

        # Clear with empty string
        r2 = c.put("/api/settings", json={"warehouse_path": ""})
        assert r2.status_code == 200
        body = r2.json()
        assert body["warehouse_path_source"] == "env"
        assert body["warehouse_path"] == str(env_wh.resolve())

        # Clear with explicit null also works
        r3 = c.put("/api/settings", json={"warehouse_path": None})
        assert r3.status_code == 200
        assert r3.json()["warehouse_path_source"] == "env"


def test_warehouse_list_uses_db_override_when_set(env_paths):
    """Setting the DB override changes /api/warehouse output without restart."""
    wh = env_paths / "wh"
    wh.mkdir()
    df = pd.DataFrame({"x": [1, 2, 3]})
    df.to_csv(wh / "demo.csv", index=False)

    with _mk_client() as c:
        # No warehouse yet -> empty list
        r0 = c.get("/api/warehouse")
        assert r0.status_code == 200
        assert r0.json()["entries"] == []
        assert r0.json()["warehouse_path"] == ""

        # Set via /api/settings
        r1 = c.put("/api/settings", json={"warehouse_path": str(wh)})
        assert r1.status_code == 200

        # /api/warehouse now reflects the new path
        r2 = c.get("/api/warehouse")
        assert r2.status_code == 200
        body = r2.json()
        assert body["warehouse_path"] == str(wh.resolve())
        rel_paths = {e["rel_path"] for e in body["entries"]}
        assert "demo.csv" in rel_paths
