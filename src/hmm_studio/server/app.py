"""FastAPI app factory: routes + lifespan + dependency wiring."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from hmm_studio.server.db import create_db_engine, get_session
from hmm_studio.server.jobs import JobRunner, _load_topology_from_yaml_str
from hmm_studio.server.models import Dataset, FitJob
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
            covariate_names=req.covariate_names,
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

    @app.get("/api/fit/{job_id}/transmat")
    def get_fit_transmat(job_id: str):
        """Return the fitted transition matrix + state labels for visualization."""
        import pickle

        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if status["status"] != "done":
            raise HTTPException(
                status_code=409,
                detail=f"job status is {status['status']!r}, not done",
            )
        result_path = status.get("result_path")
        if not result_path:
            raise HTTPException(status_code=500, detail="result_path missing")
        with (Path(result_path) / "model.pkl").open("rb") as f:
            fitted = pickle.load(f)
        topology = fitted.topology
        transmat = fitted.model.transmat_.tolist()
        mask = topology.transition_mask().tolist()
        return {
            "state_names": list(topology.state_names),
            "transmat": transmat,
            "mask": mask,
            "n_states": topology.n_states,
        }

    @app.get("/api/fit/{job_id}/decoded")
    def get_fit_decoded(job_id: str):
        """Return Viterbi path + posterior for visualization."""
        import pickle

        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if status["status"] != "done":
            raise HTTPException(
                status_code=409,
                detail=f"job status is {status['status']!r}, not done",
            )
        result_path = status.get("result_path")
        if not result_path:
            raise HTTPException(status_code=500, detail="result_path missing")
        with (Path(result_path) / "model.pkl").open("rb") as f:
            fitted = pickle.load(f)
        with get_session(engine) as session:
            job = session.get(FitJob, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="job not found")
            dataset = session.get(Dataset, job.dataset_id)
            if dataset is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"original dataset {job.dataset_id} missing",
                )
            dataset_path = dataset.path
        df = pd.read_csv(dataset_path)
        if fitted.topology.emission.type == "multinomial":
            X = df.to_numpy(dtype=int)
        else:
            X = df.to_numpy(dtype=float)
        viterbi = fitted.model.predict(X).tolist()
        posterior = fitted.model.predict_proba(X)
        n = len(viterbi)
        step = max(1, n // 2000)
        viterbi_ds = viterbi[::step]
        posterior_ds = posterior[::step].tolist()
        return {
            "viterbi": viterbi_ds,
            "posterior": posterior_ds,
            "n_total": n,
            "step": step,
            "state_names": list(fitted.topology.state_names),
        }

    @app.get("/api/fit/{job_id}/emissions")
    def get_fit_emissions(job_id: str):
        """Return per-state emission parameters for display."""
        import pickle

        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if status["status"] != "done":
            raise HTTPException(
                status_code=409, detail=f"status: {status['status']}"
            )
        result_path = status.get("result_path")
        if not result_path:
            raise HTTPException(status_code=500, detail="result_path missing")
        with (Path(result_path) / "model.pkl").open("rb") as f:
            fitted = pickle.load(f)
        e_type = fitted.topology.emission.type
        model = fitted.model
        payload: dict = {
            "type": e_type,
            "state_names": list(fitted.topology.state_names),
        }
        if e_type in ("gaussian", "gmm"):
            payload["means"] = np.asarray(model.means_).tolist()
            covars = model._covars_ if hasattr(model, "_covars_") else model.covars_
            payload["covars"] = np.asarray(covars).tolist()
        elif e_type == "multinomial":
            payload["emissionprob"] = np.asarray(model.emissionprob_).tolist()
        elif e_type == "poisson":
            payload["lambdas"] = np.asarray(model.lambdas_).tolist()
        return payload

    @app.get("/api/fit/{job_id}/A_at")
    def get_fit_a_at(job_id: str, t: int = 0):
        """Return the K x K transition matrix at time index t (NHMM only).

        Returns 404 if the job is not an NHMM fit (no nhmm.pkl present).
        """
        import pickle

        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if status["status"] != "done":
            raise HTTPException(status_code=409, detail=f"status: {status['status']}")
        result_path = status.get("result_path")
        if not result_path:
            raise HTTPException(status_code=500, detail="result_path missing")
        nhmm_pkl = Path(result_path) / "nhmm.pkl"
        if not nhmm_pkl.exists():
            raise HTTPException(status_code=404, detail="not an NHMM fit")
        with nhmm_pkl.open("rb") as f:
            nhmm = pickle.load(f)
        if t < 0 or t >= len(nhmm.A_t):
            raise HTTPException(
                status_code=400,
                detail=f"t={t} out of range [0, {len(nhmm.A_t)})",
            )
        return {
            "t": t,
            "T": len(nhmm.A_t),
            "A": nhmm.A_t[t].tolist(),
            "state_names": list(nhmm.base.topology.state_names),
            "covariate_names": list(nhmm.covariate_names),
        }

    @app.get("/api/fit/{job_id}/nhmm_info")
    def get_fit_nhmm_info(job_id: str):
        """Lightweight info: is this an NHMM fit? T length? covariate names?"""
        import pickle

        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if status["status"] != "done":
            return {"is_nhmm": False, "reason": f"status: {status['status']}"}
        result_path = status.get("result_path")
        if not result_path:
            return {"is_nhmm": False, "reason": "result_path missing"}
        nhmm_pkl = Path(result_path) / "nhmm.pkl"
        if not nhmm_pkl.exists():
            return {"is_nhmm": False}
        with nhmm_pkl.open("rb") as f:
            nhmm = pickle.load(f)
        return {
            "is_nhmm": True,
            "T": len(nhmm.A_t),
            "n_states": nhmm.n_states,
            "covariate_names": list(nhmm.covariate_names),
            "state_names": list(nhmm.base.topology.state_names),
        }

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
