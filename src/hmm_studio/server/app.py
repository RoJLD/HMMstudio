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
from hmm_studio.server.models import Annotation, Dataset, FitJob, FitJobStatus, SettingsRow
from hmm_studio.server.schemas import (
    AnnotationOut,
    AnnotationsResponse,
    DatasetPreview,
    FitJobCreate,
    FitJobResult,
    FitJobScanCreate,
    ScanChildStatus,
    ScanResult,
    SettingsResponse,
    SettingsUpdate,
    TopologyValidateRequest,
    TopologyValidateResponse,
    WarehouseEntryOut,
    WarehouseListResponse,
    WarehousePreviewResponse,
    WarehouseSidecarMeta,
)
from hmm_studio.server.warehouse import (
    get_scan_cache,
    load_sidecar,
    read_dataset,
    safe_resolve,
    write_sidecar,
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

    def _resolve_warehouse_path() -> Path | None:
        """Resolve the active warehouse_path: DB override > env var > None.

        Read on each request so settings updates take effect without a server
        restart. The DB value (if non-empty) wins; otherwise fall back to
        ``HMM_STUDIO_WAREHOUSE_PATH``; otherwise return ``None``.
        """
        db_value: str | None = None
        with get_session(engine) as session:
            row = session.get(SettingsRow, "global")
            if row is not None:
                db_value = row.warehouse_path
        if db_value:
            return Path(db_value).expanduser().resolve()
        env_value = os.environ.get("HMM_STUDIO_WAREHOUSE_PATH", "")
        if env_value:
            return Path(env_value).expanduser().resolve()
        return None

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

    def _store_dataframe_as_dataset(df: pd.DataFrame, filename: str) -> DatasetPreview:
        """Persist a DataFrame as a Dataset row + CSV file in uploads_dir.

        Used by both ``/api/data/upload`` (raw upload) and
        ``/api/warehouse/{rel_path}/promote`` (warehouse-sourced) so the
        downstream fit pipeline can consume either by ``dataset_id``.
        """
        dataset_id = str(uuid.uuid4())
        path = uploads_dir / f"{dataset_id}.csv"
        df.to_csv(path, index=False)
        dtypes_map = {c: str(df[c].dtype) for c in df.columns}
        ds = Dataset(
            id=dataset_id,
            filename=filename,
            n_rows=len(df),
            n_cols=len(df.columns),
            dtypes=json.dumps(dtypes_map),
            path=str(path),
        )
        with get_session(engine) as session:
            session.add(ds)
            session.commit()
            session.refresh(ds)
            ds_id = ds.id
            ds_filename = ds.filename
            ds_n_rows = ds.n_rows
            ds_n_cols = ds.n_cols
        head = df.head(10)
        return DatasetPreview(
            id=ds_id,
            filename=ds_filename,
            n_rows=ds_n_rows,
            n_cols=ds_n_cols,
            columns=list(df.columns),
            dtypes=dtypes_map,
            head=head.where(head.notna(), None).to_dict(orient="records"),
        )

    @app.post("/api/data/upload", response_model=DatasetPreview)
    def upload_dataset(file: UploadFile = File(...)):
        contents = file.file.read()
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="file too large (max 50MB)")
        # Stage incoming bytes via a temp path so pandas can parse them; then
        # delegate to the shared helper which (re-)writes the canonical CSV.
        import io

        df = pd.read_csv(io.BytesIO(contents))
        return _store_dataframe_as_dataset(df, file.filename or "uploaded.csv")

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
            lengths=req.lengths,
        )
        status = runner.get_status(job_id)
        with get_session(engine) as session:
            job = session.get(FitJob, status["id"])
            dataset_id = job.dataset_id if job else None
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
            dataset_id=dataset_id,
        )

    @app.get("/api/fit/{job_id}", response_model=FitJobResult)
    def get_fit_status(job_id: str):
        try:
            status = runner.get_status(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        with get_session(engine) as session:
            job = session.get(FitJob, job_id)
            dataset_id = job.dataset_id if job else None
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
            dataset_id=dataset_id,
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
            raise HTTPException(status_code=409, detail=f"status: {status['status']}")
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

    @app.post("/api/fit/scan/start", response_model=dict)
    def start_scan(req: FitJobScanCreate):
        with get_session(engine) as session:
            ds = session.get(Dataset, req.dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
        try:
            parent_id = runner.submit_scan(
                topology_yaml=req.topology_yaml,
                dataset_id=req.dataset_id,
                k_min=req.k_min,
                k_max=req.k_max,
                seed=req.seed,
                covariate_names=req.covariate_names,
                lengths=req.lengths,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"parent_id": parent_id}

    @app.get("/api/fit/scan/{parent_id}", response_model=ScanResult)
    def get_scan(parent_id: str):
        from sqlmodel import select

        with get_session(engine) as session:
            parent = session.get(FitJob, parent_id)
            if parent is None or parent.parent_id is not None:
                raise HTTPException(status_code=404, detail="scan parent not found")
            parent_status = parent.status
            # Snapshot child fields inside the session to avoid DetachedInstanceError
            raw_children = [
                {"id": c.id, "k_override": c.k_override}
                for c in session.exec(select(FitJob).where(FitJob.parent_id == parent_id)).all()
            ]

        raw_children.sort(key=lambda x: x["k_override"] or 0)

        child_statuses = []
        for c in raw_children:
            ch = runner.get_status(c["id"])
            child_statuses.append(
                ScanChildStatus(
                    job_id=c["id"],
                    k=c["k_override"] or 0,
                    status=ch["status"],
                    log_likelihood=ch.get("log_likelihood"),
                    bic=ch.get("bic"),
                    aic=ch.get("aic"),
                    converged=ch.get("converged"),
                    n_iter_actual=ch.get("n_iter_actual"),
                    error=ch.get("error"),
                )
            )

        # Best K by BIC / AIC (lower is better) among done children
        done = [c for c in child_statuses if c.status == "done" and c.bic is not None]
        best_bic = min(done, key=lambda c: c.bic).k if done else None
        done_a = [c for c in child_statuses if c.status == "done" and c.aic is not None]
        best_aic = min(done_a, key=lambda c: c.aic).k if done_a else None

        # Derive overall status from children (may be more up-to-date than parent row)
        if parent_status == FitJobStatus.RUNNING:
            statuses = [c.status for c in child_statuses]
            if not statuses or any(s in ("queued", "running") for s in statuses):
                overall = "running"
            elif all(s == "failed" for s in statuses):
                overall = "failed"
            else:
                overall = "done"
        else:
            overall = parent_status.value if hasattr(parent_status, "value") else str(parent_status)

        return ScanResult(
            parent_id=parent_id,
            k_min=min(c.k for c in child_statuses) if child_statuses else 0,
            k_max=max(c.k for c in child_statuses) if child_statuses else 0,
            overall_status=overall,
            children=child_statuses,
            best_k_by_bic=best_bic,
            best_k_by_aic=best_aic,
        )

    @app.post("/api/data/{dataset_id}/annotations/upload", response_model=AnnotationsResponse)
    def upload_annotations(dataset_id: str, file: UploadFile = File(...)):
        """Upload a CSV with columns `t,label[,color]`. Replaces existing annotations.

        Each row creates one Annotation. Existing annotations for the dataset
        are deleted first (upload is idempotent — re-uploading replaces).
        """
        with get_session(engine) as session:
            ds = session.get(Dataset, dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
            n_rows = ds.n_rows

        contents = file.file.read()
        if len(contents) > 1 * 1024 * 1024:  # 1MB cap for annotations
            raise HTTPException(status_code=413, detail="annotations file too large (max 1MB)")

        import io as _io

        try:
            df = pd.read_csv(_io.BytesIO(contents))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"failed to parse CSV: {exc}")

        if "t" not in df.columns or "label" not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="CSV must have columns 't' and 'label' (color optional)",
            )

        # Validate t is in range
        try:
            df["t"] = df["t"].astype(int)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=f"column 't' must be integer: {exc}")
        if df["t"].min() < 0 or df["t"].max() >= n_rows:
            raise HTTPException(
                status_code=400,
                detail=f"t values must be in [0, {n_rows}); got [{int(df['t'].min())}, {int(df['t'].max())}]",
            )

        with get_session(engine) as session:
            from sqlmodel import select

            # Delete existing
            existing = list(
                session.exec(select(Annotation).where(Annotation.dataset_id == dataset_id)).all()
            )
            for a in existing:
                session.delete(a)

            # Insert new
            out: list[AnnotationOut] = []
            for _, row in df.iterrows():
                ann = Annotation(
                    dataset_id=dataset_id,
                    t=int(row["t"]),
                    label=str(row["label"]),
                    color=(
                        str(row["color"])
                        if "color" in df.columns and pd.notna(row["color"])
                        else None
                    ),
                )
                session.add(ann)
                session.commit()
                session.refresh(ann)
                out.append(
                    AnnotationOut(
                        id=ann.id,
                        dataset_id=ann.dataset_id,
                        t=ann.t,
                        label=ann.label,
                        color=ann.color,
                    )
                )

        return AnnotationsResponse(dataset_id=dataset_id, annotations=out)

    @app.get("/api/data/{dataset_id}/annotations", response_model=AnnotationsResponse)
    def list_annotations(dataset_id: str):
        with get_session(engine) as session:
            ds = session.get(Dataset, dataset_id)
            if ds is None:
                raise HTTPException(status_code=404, detail="dataset not found")
            from sqlmodel import select

            anns = list(
                session.exec(select(Annotation).where(Annotation.dataset_id == dataset_id)).all()
            )
            out = [
                AnnotationOut(
                    id=a.id,
                    dataset_id=a.dataset_id,
                    t=a.t,
                    label=a.label,
                    color=a.color,
                )
                for a in sorted(anns, key=lambda x: x.t)
            ]
        return AnnotationsResponse(dataset_id=dataset_id, annotations=out)

    @app.delete("/api/data/{dataset_id}/annotations/{annotation_id}")
    def delete_annotation(dataset_id: str, annotation_id: str):
        with get_session(engine) as session:
            ann = session.get(Annotation, annotation_id)
            if ann is None or ann.dataset_id != dataset_id:
                raise HTTPException(status_code=404, detail="annotation not found")
            session.delete(ann)
        return {"deleted": annotation_id}

    # -----------------------------------------------------------------------
    # Settings endpoints
    # -----------------------------------------------------------------------

    def _settings_response() -> SettingsResponse:
        """Build a SettingsResponse from the current DB row + env var.

        Source precedence: DB (non-empty) > env (non-empty) > unset.
        """
        with get_session(engine) as session:
            row = session.get(SettingsRow, "global")
            db_value = row.warehouse_path if row is not None else None
            updated_at = row.updated_at.isoformat() if row is not None else None
        env_value = os.environ.get("HMM_STUDIO_WAREHOUSE_PATH", "") or None
        if db_value:
            resolved = str(Path(db_value).expanduser().resolve())
            source = "db"
        elif env_value:
            resolved = str(Path(env_value).expanduser().resolve())
            source = "env"
        else:
            resolved = None
            source = "unset"
        return SettingsResponse(
            warehouse_path=resolved,
            warehouse_path_source=source,
            warehouse_path_env=env_value,
            updated_at=updated_at,
        )

    @app.get("/api/settings", response_model=SettingsResponse)
    def get_settings():
        """Return current settings; resolves warehouse_path from DB > env > None."""
        return _settings_response()

    @app.put("/api/settings", response_model=SettingsResponse)
    def update_settings(payload: SettingsUpdate):
        """Update user settings.

        Validation: if ``warehouse_path`` is a non-empty string, it must exist
        and be a directory. An empty string or ``None`` clears the DB override
        (settings then fall back to the env var or unset).
        """
        new_value: str | None
        raw = payload.warehouse_path
        if raw is None or raw == "":
            new_value = None
        else:
            try:
                candidate = Path(raw).expanduser().resolve()
            except (OSError, RuntimeError) as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"warehouse_path is not a valid path: {raw} ({exc})",
                )
            if not candidate.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"warehouse_path does not exist: {candidate}",
                )
            if not candidate.is_dir():
                raise HTTPException(
                    status_code=400,
                    detail=f"warehouse_path is not a directory: {candidate}",
                )
            new_value = str(candidate)

        from datetime import datetime as _dt

        with get_session(engine) as session:
            row = session.get(SettingsRow, "global")
            if row is None:
                row = SettingsRow(id="global", warehouse_path=new_value, updated_at=_dt.utcnow())
                session.add(row)
            else:
                row.warehouse_path = new_value
                row.updated_at = _dt.utcnow()
                session.add(row)

        # Invalidate the warehouse scan cache so a new path takes effect immediately.
        get_scan_cache().invalidate()
        return _settings_response()

    # -----------------------------------------------------------------------
    # Warehouse endpoints
    # -----------------------------------------------------------------------

    @app.get("/api/warehouse", response_model=WarehouseListResponse)
    def list_warehouse():
        warehouse_path = _resolve_warehouse_path()
        if warehouse_path is None or not warehouse_path.exists():
            return WarehouseListResponse(warehouse_path="", entries=[])
        cache = get_scan_cache()
        entries = cache.get_or_scan(warehouse_path)
        return WarehouseListResponse(
            warehouse_path=str(warehouse_path),
            entries=[WarehouseEntryOut(**e.to_dict()) for e in entries],
        )

    @app.post("/api/warehouse/refresh", response_model=WarehouseListResponse)
    def refresh_warehouse():
        cache = get_scan_cache()
        cache.invalidate()
        return list_warehouse()

    @app.get("/api/warehouse/{rel_path:path}/preview", response_model=WarehousePreviewResponse)
    def get_warehouse_preview(rel_path: str, n: int = 10):
        warehouse_path = _resolve_warehouse_path()
        if warehouse_path is None:
            raise HTTPException(status_code=400, detail="warehouse_path not configured")
        try:
            full = safe_resolve(warehouse_path, rel_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not full.exists() or not full.is_file():
            raise HTTPException(status_code=404, detail="dataset not found")
        try:
            df = read_dataset(full)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"failed to read dataset: {exc}")
        head = df.head(n)
        return WarehousePreviewResponse(
            rel_path=rel_path,
            n_rows_total=len(df),
            n_cols=len(df.columns),
            columns=list(df.columns),
            dtypes={c: str(df[c].dtype) for c in df.columns},
            head=head.where(head.notna(), None).to_dict(orient="records"),
        )

    @app.get("/api/warehouse/{rel_path:path}/meta")
    def get_warehouse_meta(rel_path: str):
        warehouse_path = _resolve_warehouse_path()
        if warehouse_path is None:
            raise HTTPException(status_code=400, detail="warehouse_path not configured")
        try:
            full = safe_resolve(warehouse_path, rel_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not full.exists() or not full.is_file():
            raise HTTPException(status_code=404, detail="dataset not found")
        sidecar = load_sidecar(full)
        return {"rel_path": rel_path, "sidecar": sidecar}

    @app.put("/api/warehouse/{rel_path:path}/meta")
    def put_warehouse_meta(rel_path: str, meta: WarehouseSidecarMeta):
        warehouse_path = _resolve_warehouse_path()
        if warehouse_path is None:
            raise HTTPException(status_code=400, detail="warehouse_path not configured")
        try:
            full = safe_resolve(warehouse_path, rel_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not full.exists() or not full.is_file():
            raise HTTPException(status_code=404, detail="dataset not found")
        write_sidecar(full, meta.model_dump(exclude_none=True))
        return {"rel_path": rel_path, "sidecar_written": True}

    @app.post("/api/warehouse/upload")
    def upload_to_warehouse(file: UploadFile = File(...), subdir: str = ""):
        """Upload a new dataset into the warehouse.

        - ``subdir`` is an optional relative sub-directory; created if missing.
        - The file name is preserved.
        - Refuses if no warehouse configured or path-traversal in subdir.
        """
        warehouse_path = _resolve_warehouse_path()
        if warehouse_path is None:
            raise HTTPException(status_code=400, detail="warehouse_path not configured")
        try:
            target_dir = safe_resolve(warehouse_path, subdir) if subdir else warehouse_path
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = file.filename or "uploaded"
        target = target_dir / filename
        # Re-resolve to ensure the final path is still inside warehouse
        try:
            safe_resolve(warehouse_path, str(target.relative_to(warehouse_path)))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        contents = file.file.read()
        if len(contents) > 200 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="file too large (max 200 MB)")
        target.write_bytes(contents)
        get_scan_cache().invalidate()
        return {
            "rel_path": str(target.relative_to(warehouse_path)).replace("\\", "/"),
            "size_bytes": len(contents),
        }

    @app.post(
        "/api/warehouse/{rel_path:path}/promote",
        response_model=DatasetPreview,
    )
    def promote_warehouse_dataset(rel_path: str):
        """Load a warehouse file into the studio's Dataset table.

        After promotion, the returned ``dataset_id`` can be passed to
        ``/api/fit/start`` like any uploaded dataset. The original
        warehouse file is left untouched; we copy the parsed frame into
        ``uploads_dir`` as a canonical CSV.
        """
        warehouse_path = _resolve_warehouse_path()
        if warehouse_path is None:
            raise HTTPException(status_code=400, detail="warehouse_path not configured")
        try:
            full = safe_resolve(warehouse_path, rel_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if not full.exists() or not full.is_file():
            raise HTTPException(status_code=404, detail="dataset not found")
        try:
            df = read_dataset(full)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"failed to read dataset: {exc}")
        return _store_dataframe_as_dataset(df, full.name)

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
