"""FastAPI app factory: routes + lifespan + dependency wiring."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from hmm_studio.server.db import create_db_engine, get_session
from hmm_studio.server.jobs import JobRunner, _load_topology_from_yaml_str
from hmm_studio.server.models import Dataset
from hmm_studio.server.schemas import (
    DatasetPreview,
    FitJobCreate,
    FitJobResult,
    TopologyValidateRequest,
    TopologyValidateResponse,
)


def _default_root() -> Path:
    return Path.home() / ".hmm-studio"


def _resolve_paths():
    root = _default_root()
    db_path = Path(os.environ.get("HMM_STUDIO_DB_PATH", str(root / "studio.db")))
    results_dir = Path(os.environ.get("HMM_STUDIO_RESULTS_DIR", str(root / "results")))
    uploads_dir = Path(os.environ.get("HMM_STUDIO_UPLOADS_DIR", str(root / "uploads")))
    return db_path, results_dir, uploads_dir


def create_app() -> FastAPI:
    """Create a FastAPI app with all routes wired."""
    db_path, results_dir, uploads_dir = _resolve_paths()
    results_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(db_path)
    runner = JobRunner(engine=engine, results_dir=results_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        runner.shutdown(wait=False)

    app = FastAPI(title="hmm-studio", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/topology/validate", response_model=TopologyValidateResponse)
    def validate_topology(req: TopologyValidateRequest):
        try:
            topo = _load_topology_from_yaml_str(req.yaml_content)
        except Exception as exc:
            return TopologyValidateResponse(valid=False, error=str(exc), summary=None)
        return TopologyValidateResponse(
            valid=True,
            error=None,
            summary=(
                f"valid: {topo.name} " f"(n_states={topo.n_states}, emission={topo.emission.type})"
            ),
        )

    @app.post("/api/data/upload", response_model=DatasetPreview)
    def upload_dataset(file: UploadFile = File(...)):
        contents = file.file.read()
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="file too large (max 50MB)")
        dataset_id = str(uuid.uuid4())
        path = uploads_dir / f"{dataset_id}.csv"
        path.write_bytes(contents)
        df = pd.read_csv(path)
        dtypes_map = {c: str(df[c].dtype) for c in df.columns}
        ds = Dataset(
            id=dataset_id,
            filename=file.filename or "uploaded.csv",
            n_rows=len(df),
            n_cols=len(df.columns),
            dtypes=json.dumps(dtypes_map),
            path=str(path),
        )
        with get_session(engine) as session:
            session.add(ds)
            session.commit()
            session.refresh(ds)
            # Capture all attributes inside the session to avoid DetachedInstanceError
            ds_id = ds.id
            ds_filename = ds.filename
            ds_n_rows = ds.n_rows
            ds_n_cols = ds.n_cols
        return DatasetPreview(
            id=ds_id,
            filename=ds_filename,
            n_rows=ds_n_rows,
            n_cols=ds_n_cols,
            columns=list(df.columns),
            dtypes=dtypes_map,
            head=df.head(10).to_dict(orient="records"),
        )

    @app.get("/api/data/{dataset_id}/preview", response_model=DatasetPreview)
    def get_dataset_preview(dataset_id: str):
        with get_session(engine) as session:
            ds = session.get(Dataset, dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
            df = pd.read_csv(ds.path)
            return DatasetPreview(
                id=ds.id,
                filename=ds.filename,
                n_rows=ds.n_rows,
                n_cols=ds.n_cols,
                columns=list(df.columns),
                dtypes={c: str(df[c].dtype) for c in df.columns},
                head=df.head(10).to_dict(orient="records"),
            )

    @app.post("/api/fit/start", response_model=FitJobResult)
    def start_fit(req: FitJobCreate):
        with get_session(engine) as session:
            ds = session.get(Dataset, req.dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
        job_id = runner.submit(
            topology_yaml=req.topology_yaml,
            dataset_id=req.dataset_id,
            seed=req.seed,
        )
        status = runner.get_status(job_id)
        return FitJobResult(
            id=status["id"],
            status=status["status"],
            log_likelihood=status.get("log_likelihood"),
            bic=status.get("bic"),
            aic=status.get("aic"),
            n_iter_actual=status.get("n_iter_actual"),
            converged=status.get("converged"),
            result_path=status.get("result_path"),
            error=status.get("error"),
        )

    @app.get("/api/fit/{job_id}", response_model=FitJobResult)
    def get_fit_status(job_id: str):
        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        return FitJobResult(
            id=status["id"],
            status=status["status"],
            log_likelihood=status.get("log_likelihood"),
            bic=status.get("bic"),
            aic=status.get("aic"),
            n_iter_actual=status.get("n_iter_actual"),
            converged=status.get("converged"),
            result_path=status.get("result_path"),
            error=status.get("error"),
        )

    @app.websocket("/ws/fit/{job_id}")
    async def ws_fit_progress(websocket: WebSocket, job_id: str):
        """Stream progress for an in-flight fit job. Closes when terminal."""
        await websocket.accept()
        try:
            while True:
                try:
                    status = runner.get_status(job_id)
                except KeyError:
                    await websocket.send_json({"error": "job not found"})
                    await websocket.close(code=1008)
                    return
                await websocket.send_json(
                    {
                        "id": status["id"],
                        "status": status["status"],
                        "progress": status["progress"],
                        "log_likelihood": status.get("log_likelihood"),
                        "bic": status.get("bic"),
                        "error": status.get("error"),
                    }
                )
                if status["status"] in ("done", "failed", "cancelled"):
                    await websocket.close()
                    return
                await asyncio.sleep(0.2)
        except WebSocketDisconnect:
            return

    # Mount the React frontend build at /, if available. The catch-all route
    # serves index.html for any path not handled by /api/* or /ws/* so React
    # Router can handle client-side routing.
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and (static_dir / "index.html").exists():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        # Mount /assets explicitly so Vite-built assets resolve.
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        # Catch-all for non-API routes -> index.html (SPA-style routing).
        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            # API and WS already handled by their respective routes. Anything
            # left should serve index.html so React Router takes over.
            return FileResponse(static_dir / "index.html")

    return app
