"""In-process job runner for hmm-studio fits.

Each `submit()` schedules a fit on a ThreadPoolExecutor. The fit's
log-likelihood history is persisted to SQLite after completion. Results
are written to a per-job directory under `results_dir`.

NOTE: B.1 does NOT stream progress mid-fit. The `progress` field is
populated only AFTER the fit completes (from `model.monitor_.history`).
B.2 (WebSocket streaming) will add real-time progress via polling.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from hmm_studio.server._time import utcnow

import numpy as np
import pandas as pd

from hmm_core import save_model
from hmm_core.fit import fit as core_fit
from hmm_core.io import load_topology as _load_topology_from_path
from hmm_core.topology import Topology
from hmm_studio.server.db import get_session
from hmm_studio.server.models import Dataset, FitJob, FitJobStatus

_DEFAULT_WORKERS = max(1, (os.cpu_count() or 2) // 2)


def _load_topology_from_yaml_str(yaml_str: str) -> Topology:
    """Parse a YAML string into a validated Topology via a temp file.

    Reuses hmm_core.io.load_topology which expects a path; we write the
    string to a temp file and clean up. Raises TopologyError on invalid.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(yaml_str)
        tmp_path = tf.name
    try:
        return _load_topology_from_path(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _topology_with_overridden_k(topology: Topology, new_k: int) -> Topology:
    """Return a copy of `topology` with n_states=new_k.

    State names become s0..s{new_k-1}; allowed_transitions are rebuilt as
    fully ergodic on the new state set (K-scan compares model capacity, not
    topology shape). Per-state emissions and transmat prior are dropped since
    they are K-dependent.
    """
    from dataclasses import replace

    new_state_names = [f"s{i}" for i in range(new_k)]
    return replace(
        topology,
        n_states=new_k,
        state_names=new_state_names,
        allowed_transitions=None,  # ergodic for K-scan
        emissions=None,  # drop per-state emissions (K-dependent)
        transmat_prior_matrix=None,  # drop prior (K-dependent)
    )


def _topology_with_overridden_emission(
    topology: Topology, emission_type: str, new_k: int, n_mix: int | None
) -> Topology:
    """Return a copy of `topology` with emission family + n_states overridden.

    Mirrors hmm_core.selection.auto_grid's per-cell logic: swap emission.type
    (and n_mix for gmm), set n_states=new_k with ergodic s0..s{k-1} state names,
    and drop the K-dependent fields (allowed_transitions, per-state emissions,
    transmat prior). n_features / covariance_type carry over from the base.
    """
    from dataclasses import replace

    new_emission = replace(
        topology.emission,
        type=emission_type,
        n_mix=(n_mix if emission_type == "gmm" else None),
    )
    return replace(
        topology,
        n_states=new_k,
        state_names=[f"s{i}" for i in range(new_k)],
        allowed_transitions=None,
        emission=new_emission,
        emissions=None,
        transmat_prior_matrix=None,
    )


def _update_scan_parent_status(engine, parent_id: str) -> None:
    """Recompute parent status from children. Idempotent."""
    from sqlmodel import select

    with get_session(engine) as session:
        children = list(session.exec(select(FitJob).where(FitJob.parent_id == parent_id)).all())
        if not children:
            return
        # Snapshot statuses inside the session to avoid DetachedInstanceError
        statuses = [c.status for c in children]
        if any(s == FitJobStatus.RUNNING for s in statuses) or any(
            s == FitJobStatus.QUEUED for s in statuses
        ):
            return  # still in progress
        parent = session.get(FitJob, parent_id)
        if parent is None:
            return
        if any(s == FitJobStatus.FAILED for s in statuses) and not all(
            s == FitJobStatus.FAILED for s in statuses
        ):
            parent.status = FitJobStatus.DONE  # partial success
        elif all(s == FitJobStatus.FAILED for s in statuses):
            parent.status = FitJobStatus.FAILED
        else:
            parent.status = FitJobStatus.DONE
        parent.ended_at = utcnow()
        session.add(parent)
        session.commit()


class JobRunner:
    """Wraps a ThreadPoolExecutor with SQLite persistence."""

    def __init__(self, engine, results_dir, max_workers: int = _DEFAULT_WORKERS):
        self._engine = engine
        self._results_dir = Path(results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        topology_yaml: str,
        dataset_id: str,
        seed=None,
        covariate_names: list[str] | None = None,
        lengths: list[int] | None = None,
    ) -> str:
        """Create a FitJob row + schedule the fit. Returns job_id."""
        with get_session(self._engine) as session:
            job = FitJob(
                topology=topology_yaml,
                dataset_id=dataset_id,
                seed=seed,
                status=FitJobStatus.QUEUED,
                covariate_names=json.dumps(covariate_names) if covariate_names else "",
                lengths=json.dumps(lengths) if lengths else "",
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

        future = self._executor.submit(self._run, job_id)
        with self._lock:
            self._futures[job_id] = future
        return job_id

    def submit_scan(
        self,
        topology_yaml: str,
        dataset_id: str,
        k_min: int,
        k_max: int,
        seed: int | None = None,
        covariate_names: list[str] | None = None,
        lengths: list[int] | None = None,
    ) -> str:
        """Create a parent job + K child jobs, one per K in [k_min, k_max].

        The parent is just a logical grouping; its status is derived from children.
        Each child runs the standard fit pipeline with its topology's n_states
        overridden to K.
        """
        if k_min < 1 or k_max < k_min:
            raise ValueError(f"invalid k range: k_min={k_min}, k_max={k_max}")

        # Create parent
        with get_session(self._engine) as session:
            parent = FitJob(
                topology=topology_yaml,
                dataset_id=dataset_id,
                seed=seed,
                status=FitJobStatus.QUEUED,
                covariate_names=json.dumps(covariate_names) if covariate_names else "",
                lengths=json.dumps(lengths) if lengths else "",
            )
            session.add(parent)
            session.commit()
            session.refresh(parent)
            parent_id = parent.id

        # Create children + schedule them
        for k in range(k_min, k_max + 1):
            with get_session(self._engine) as session:
                child = FitJob(
                    topology=topology_yaml,
                    dataset_id=dataset_id,
                    seed=seed,
                    status=FitJobStatus.QUEUED,
                    covariate_names=json.dumps(covariate_names) if covariate_names else "",
                    lengths=json.dumps(lengths) if lengths else "",
                    parent_id=parent_id,
                    k_override=k,
                )
                session.add(child)
                session.commit()
                session.refresh(child)
                child_id = child.id
            future = self._executor.submit(self._run, child_id)
            with self._lock:
                self._futures[child_id] = future

        # Mark parent as running once children scheduled
        with get_session(self._engine) as session:
            parent = session.get(FitJob, parent_id)
            parent.status = FitJobStatus.RUNNING
            parent.started_at = utcnow()
            session.add(parent)
            session.commit()

        return parent_id

    def submit_compare(
        self,
        topology_yaml: str,
        dataset_id: str,
        k_min: int,
        k_max: int,
        emission_types: list[str],
        n_mix: int = 2,
        seed: int | None = None,
        lengths: list[int] | None = None,
    ) -> str:
        """Create a parent + one child per (emission_type, K) cell.

        Each child models P(X) (comparable grid). Children reuse the base
        topology YAML and override emission family + K at fit time.
        """
        if k_min < 1 or k_max < k_min:
            raise ValueError(f"invalid k range: k_min={k_min}, k_max={k_max}")
        if not emission_types:
            raise ValueError("emission_types must be non-empty")

        with get_session(self._engine) as session:
            parent = FitJob(
                topology=topology_yaml,
                dataset_id=dataset_id,
                seed=seed,
                status=FitJobStatus.QUEUED,
                lengths=json.dumps(lengths) if lengths else "",
            )
            session.add(parent)
            session.commit()
            session.refresh(parent)
            parent_id = parent.id

        for etype in emission_types:
            for k in range(k_min, k_max + 1):
                with get_session(self._engine) as session:
                    child = FitJob(
                        topology=topology_yaml,
                        dataset_id=dataset_id,
                        seed=seed,
                        status=FitJobStatus.QUEUED,
                        lengths=json.dumps(lengths) if lengths else "",
                        parent_id=parent_id,
                        k_override=k,
                        emission_override=etype,
                        n_mix_override=(n_mix if etype == "gmm" else None),
                    )
                    session.add(child)
                    session.commit()
                    session.refresh(child)
                    child_id = child.id
                future = self._executor.submit(self._run, child_id)
                with self._lock:
                    self._futures[child_id] = future

        with get_session(self._engine) as session:
            parent = session.get(FitJob, parent_id)
            parent.status = FitJobStatus.RUNNING
            parent.started_at = utcnow()
            session.add(parent)
            session.commit()

        return parent_id

    def get_status(self, job_id: str) -> dict:
        """Return the latest persisted status of a job as a dict."""
        with get_session(self._engine) as session:
            job = session.get(FitJob, job_id)
            if job is None:
                raise KeyError(f"unknown job_id {job_id!r}")
            progress = json.loads(job.progress) if job.progress else []
            summary = _read_summary(job.result_path)
            return {
                "id": job.id,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "progress": progress,
                "log_likelihood": _safe_get(summary, "fit", "log_likelihood", as_=float),
                "bic": _safe_get(summary, "fit", "bic", as_=float),
                "aic": _safe_get(summary, "fit", "aic", as_=float),
                "hqic": _safe_get(summary, "fit", "hqic", as_=float),
                "n_iter_actual": _safe_get(summary, "fit", "n_iter_actual", as_=int),
                "converged": _safe_get(summary, "fit", "converged", as_=bool),
                "result_path": job.result_path,
                "error": job.error,
            }

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def _run(self, job_id: str) -> None:
        """Execute the fit for `job_id`; updates the DB row throughout."""
        job_parent_id: str | None = None  # captured early so catch-all can update parent
        try:
            # Step 1: load job + dataset
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                if job is None:
                    return
                dataset = session.get(Dataset, job.dataset_id)
                # snapshot all needed fields before session closes
                topology_yaml = job.topology
                seed = job.seed
                covariate_names_json = job.covariate_names
                lengths_raw = job.lengths
                k_override = job.k_override  # NEW: K-scan override
                emission_override = job.emission_override  # NEW: compare emission override
                n_mix_override = job.n_mix_override  # NEW: compare gmm n_mix
                job_parent_id = job.parent_id  # NEW: scan parent tracking (overrides outer None)
                if dataset is None:
                    job.status = FitJobStatus.FAILED
                    job.error = f"dataset {job.dataset_id} not found"
                    job.ended_at = utcnow()
                    session.add(job)
                    session.commit()
                    if job_parent_id is not None:
                        _update_scan_parent_status(self._engine, job_parent_id)
                    return
                dataset_path = dataset.path

            # Step 2: validate topology, possibly with overridden emission / K
            try:
                topology = _load_topology_from_yaml_str(topology_yaml)
                if emission_override is not None:
                    topology = _topology_with_overridden_emission(
                        topology,
                        emission_override,
                        k_override if k_override is not None else topology.n_states,
                        n_mix_override,
                    )
                    topology.validate()
                elif k_override is not None and k_override != topology.n_states:
                    topology = _topology_with_overridden_k(topology, k_override)
                    topology.validate()
            except Exception as exc:
                with get_session(self._engine) as session:
                    job = session.get(FitJob, job_id)
                    job.status = FitJobStatus.FAILED
                    job.error = f"invalid topology: {exc}"
                    job.ended_at = utcnow()
                    session.add(job)
                    session.commit()
                if job_parent_id is not None:
                    _update_scan_parent_status(self._engine, job_parent_id)
                return

            # Step 3: load data, split X / Z if NHMM
            df = pd.read_csv(dataset_path)
            covariate_names = json.loads(covariate_names_json) if covariate_names_json else []
            is_nhmm = bool(covariate_names)

            if is_nhmm:
                missing = [c for c in covariate_names if c not in df.columns]
                if missing:
                    raise ValueError(f"covariate columns not in CSV: {missing}")
                Z = df[covariate_names].to_numpy(dtype=float)
                obs_cols = [c for c in df.columns if c not in covariate_names]
                X_df = df[obs_cols]
                if topology.emission.type == "multinomial":
                    X = X_df.to_numpy(dtype=int)
                else:
                    X = X_df.to_numpy(dtype=float)
            else:
                Z = None
                if topology.emission.type == "multinomial":
                    X = df.to_numpy(dtype=int)
                else:
                    X = df.to_numpy(dtype=float)

            # Parse lengths for multi-sequence fits
            lengths_list = json.loads(lengths_raw) if lengths_raw else None
            lengths_arr = np.array(lengths_list, dtype=int) if lengths_list else None

            # Validate: sum(lengths) must equal len(X)
            if lengths_arr is not None and int(lengths_arr.sum()) != len(X):
                raise ValueError(f"lengths sum {int(lengths_arr.sum())} != len(X) {len(X)}")

            # Step 4: mark running
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                job.status = FitJobStatus.RUNNING
                job.started_at = utcnow()
                session.add(job)
                session.commit()

            # Step 5: run fit with mid-flight progress persistence
            def _persist_progress(history):
                try:
                    with get_session(self._engine) as session:
                        job = session.get(FitJob, job_id)
                        if job is not None:
                            job.progress = json.dumps([float(x) for x in history])
                            session.add(job)
                            session.commit()
                except Exception:
                    pass  # never let callback raise

            from hmm_core import fit_nhmm

            try:
                if is_nhmm:
                    result = fit_nhmm(
                        topology,
                        X,
                        Z,
                        covariate_names=covariate_names,
                        seed=seed,
                        lengths=lengths_arr,
                    )
                else:
                    result = core_fit(
                        topology,
                        X,
                        seed=seed,
                        lengths=lengths_arr,
                        progress_callback=_persist_progress,
                    )
            except Exception as exc:
                with get_session(self._engine) as session:
                    job = session.get(FitJob, job_id)
                    job.status = FitJobStatus.FAILED
                    job.error = f"fit error: {exc}"
                    job.ended_at = utcnow()
                    session.add(job)
                    session.commit()
                if job_parent_id is not None:
                    _update_scan_parent_status(self._engine, job_parent_id)
                return

            # Step 6: extract progress history
            # Step 7: save result bundle
            result_dir = self._results_dir / job_id
            result_dir.mkdir(parents=True, exist_ok=True)
            if is_nhmm:
                save_model(result.base, result_dir)
                import pickle as _pickle

                with (result_dir / "nhmm.pkl").open("wb") as f:
                    _pickle.dump(result, f, protocol=_pickle.HIGHEST_PROTOCOL)
                monitor = getattr(result.base.model, "monitor_", None)
            else:
                save_model(result, result_dir)
                monitor = getattr(result.model, "monitor_", None)
            history = list(getattr(monitor, "history", [])) if monitor is not None else []

            # Step 8: persist final status
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                job.status = FitJobStatus.DONE
                job.progress = json.dumps([float(x) for x in history])
                job.result_path = str(result_dir)
                job.ended_at = utcnow()
                session.add(job)
                session.commit()

            # Step 9: if this is a child of a scan, possibly update parent
            if job_parent_id is not None:
                _update_scan_parent_status(self._engine, job_parent_id)

        except Exception as exc:
            # Catch-all: persist failure
            with get_session(self._engine) as session:
                job = session.get(FitJob, job_id)
                if job is not None:
                    job.status = FitJobStatus.FAILED
                    job.error = f"unexpected error: {exc}"
                    job.ended_at = utcnow()
                    session.add(job)
                    session.commit()
            if job_parent_id is not None:
                _update_scan_parent_status(self._engine, job_parent_id)


def _read_summary(result_path: str | None) -> dict | None:
    if not result_path:
        return None
    summary_path = Path(result_path) / "summary.json"
    if not summary_path.exists():
        return None
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_get(summary: dict | None, *keys, as_=None):
    """Drill into nested dict, return None if any key missing."""
    if summary is None:
        return None
    cur = summary
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    if as_ is not None:
        try:
            return as_(cur)
        except (TypeError, ValueError):
            return None
    return cur
