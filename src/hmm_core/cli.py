"""hmm-fit CLI: validate / run / decode / show / batch."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import typer

from hmm_core.fit import fit
from hmm_core.io import load_model, load_topology, save_decoded, save_model
from hmm_core.topology import TopologyError

app = typer.Typer(help="HMM topology editor + constrained fit engine.")


def _read_observations(csv_path: Path, topology) -> np.ndarray:
    """Read a CSV and shape it for the topology's emission type."""
    df = pd.read_csv(csv_path)
    e = topology.emission
    if e.type in ("gaussian", "gmm", "poisson"):
        if df.shape[1] != e.n_features:
            raise typer.BadParameter(
                f"CSV has {df.shape[1]} columns but topology.emission.n_features={e.n_features}"
            )
        return df.to_numpy(dtype=float)
    if e.type == "multinomial":
        if df.shape[1] != 1:
            raise typer.BadParameter(
                "Multinomial expects a single-column CSV of integer symbol IDs"
            )
        X = df.to_numpy(dtype=int)
        if X.max() >= e.n_symbols or X.min() < 0:
            raise typer.BadParameter(f"symbol IDs must be in [0, n_symbols={e.n_symbols})")
        return X
    raise typer.BadParameter(f"unknown emission type: {e.type!r}")


@app.command()
def validate(topology_path: Path) -> None:
    """Load and validate a topology YAML; exit 0 if valid, 1 otherwise."""
    try:
        topo = load_topology(topology_path)
    except (TopologyError, FileNotFoundError) as exc:
        typer.echo(f"INVALID: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"valid: {topo.name} (n_states={topo.n_states}, emission={topo.emission.type})")


@app.command()
def run(
    topology_path: Path,
    data_path: Path,
    output: Path = typer.Option(..., "--output", "-o", help="Output directory"),
    seed: int = typer.Option(None, help="Override topology.init.seed"),
) -> None:
    """Fit the HMM described by topology on data; write model.pkl + summary.json."""
    topo = load_topology(topology_path)
    X = _read_observations(data_path, topo)
    result = fit(topo, X, seed=seed)
    save_model(result, output)
    typer.echo(
        f"fit done: log_lik={result.log_likelihood:.2f} BIC={result.bic:.2f} "
        f"converged={result.converged} iters={result.n_iter_actual}"
    )


@app.command()
def decode(
    model_path: Path,
    data_path: Path,
    output: Path = typer.Option(..., "--output", "-o", help="Decoded parquet path"),
) -> None:
    """Run Viterbi + posterior on new data using a fitted model."""
    fitted = load_model(model_path)
    X = _read_observations(data_path, fitted.topology)
    viterbi = fitted.model.predict(X)
    posterior = fitted.model.predict_proba(X)
    save_decoded(viterbi, posterior, pd.RangeIndex(len(X)), output)
    typer.echo(f"decoded {len(X)} observations -> {output}")


@app.command()
def show(model_path: Path) -> None:
    """Print a human-readable summary of a fitted model."""
    fitted = load_model(model_path)
    K = fitted.topology.n_states
    mask = fitted.topology.transition_mask()
    typer.echo(f"name:           {fitted.topology.name}")
    typer.echo(f"emission:       {fitted.topology.emission.type}")
    typer.echo(f"n_states:       {K}")
    typer.echo(f"log_likelihood: {fitted.log_likelihood:.4f}")
    typer.echo(f"BIC:            {fitted.bic:.4f}")
    typer.echo(f"AIC:            {fitted.aic:.4f}")
    typer.echo(f"converged:      {fitted.converged}  (iters: {fitted.n_iter_actual})")
    typer.echo("transmat (x = forbidden by mask):")
    for i in range(K):
        row = []
        for j in range(K):
            if not mask[i, j]:
                row.append("  x  ")
            else:
                row.append(f"{fitted.model.transmat_[i, j]:5.3f}")
        typer.echo(f"  {fitted.topology.state_names[i]:>10s} | " + " ".join(row))


@app.command()
def batch(
    input_dir: Path,
    output: Path = typer.Option(..., "--output", "-o", help="Output directory (one subdir per job)"),
    workers: Optional[int] = typer.Option(
        None, "--workers", "-w",
        help="Max parallel fits (default: os.cpu_count() // 2)",
    ),
    seed: Optional[int] = typer.Option(None, "--seed", help="Override topology.init.seed for all jobs"),
    pattern: str = typer.Option("*.yaml", help="Glob to find topology files in input_dir"),
) -> None:
    """Run many fits in parallel from a directory of (topology, data) pairs.

    The input directory should contain matched pairs sharing a stem:
        job_001.yaml + job_001.csv
        job_002.yaml + job_002.csv
        ...

    Each pair produces a result bundle at output/<stem>/.
    """
    import os
    from concurrent.futures import ProcessPoolExecutor, as_completed

    input_dir = input_dir.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists() or not input_dir.is_dir():
        typer.echo(f"input_dir does not exist or is not a directory: {input_dir}", err=True)
        raise typer.Exit(code=1)

    # Pair topology YAML with CSV by stem
    yaml_files = sorted(input_dir.glob(pattern))
    jobs: list[tuple[str, Path, Path]] = []
    missing: list[str] = []
    for ypath in yaml_files:
        stem = ypath.stem
        csv = input_dir / f"{stem}.csv"
        if not csv.exists():
            missing.append(stem)
            continue
        jobs.append((stem, ypath, csv))

    if missing:
        typer.echo(
            f"Skipping {len(missing)} topology files with no matching .csv: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}",
            err=True,
        )

    if not jobs:
        typer.echo("no valid (yaml, csv) pairs found in input_dir", err=True)
        raise typer.Exit(code=1)

    max_workers = workers if workers is not None else max(1, (os.cpu_count() or 2) // 2)
    typer.echo(f"Running {len(jobs)} fits with {max_workers} workers...")

    # Run all in parallel
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_one_job, stem, ypath, cpath, output, seed): stem
            for stem, ypath, cpath in jobs
        }
        for future in as_completed(futures):
            stem = futures[future]
            try:
                result = future.result()
                results.append(result)
                _print_progress_line(result)
            except Exception as exc:
                fail = {
                    "stem": stem,
                    "status": "failed",
                    "error": str(exc),
                    "log_likelihood": None,
                    "bic": None,
                    "n_iter_actual": None,
                    "duration": None,
                }
                results.append(fail)
                _print_progress_line(fail)

    # Final summary
    typer.echo("")
    typer.echo("=" * 70)
    n_done = sum(1 for r in results if r["status"] == "done")
    n_failed = sum(1 for r in results if r["status"] == "failed")
    typer.echo(f"Batch complete: {n_done} done, {n_failed} failed, {len(results)} total")
    if n_failed:
        typer.echo(f"Failed jobs: {[r['stem'] for r in results if r['status'] == 'failed']}", err=True)
        raise typer.Exit(code=1)


def _run_one_job(
    stem: str,
    yaml_path: Path,
    csv_path: Path,
    output_root: Path,
    seed: int | None,
) -> dict:
    """Worker: runs one fit, writes the bundle, returns a small summary dict.

    Lives at module level so ProcessPoolExecutor can pickle it.
    """
    import time as _time

    t0 = _time.perf_counter()
    job_output = output_root / stem
    try:
        topo = load_topology(yaml_path)
        X = _read_observations(csv_path, topo)
        result = fit(topo, X, seed=seed)
        save_model(result, job_output)
        duration = _time.perf_counter() - t0
        return {
            "stem": stem,
            "status": "done",
            "log_likelihood": result.log_likelihood,
            "bic": result.bic,
            "n_iter_actual": result.n_iter_actual,
            "duration": duration,
            "error": None,
        }
    except Exception as exc:
        duration = _time.perf_counter() - t0
        return {
            "stem": stem,
            "status": "failed",
            "log_likelihood": None,
            "bic": None,
            "n_iter_actual": None,
            "duration": duration,
            "error": str(exc),
        }


def _print_progress_line(result: dict) -> None:
    """Print a one-line update for a finished (or failed) job."""
    stem = result["stem"]
    status = result["status"]
    dur = f"{result['duration']:.1f}s" if result.get("duration") else "-"
    if status == "done":
        ll = result["log_likelihood"]
        bic = result["bic"]
        iters = result["n_iter_actual"]
        typer.echo(f"  [ok] {stem:30s} log_lik={ll:>10.2f}  BIC={bic:>10.2f}  iters={iters:3d}  ({dur})")
    else:
        typer.echo(f"  [FAIL] {stem:30s} FAILED: {result['error']}  ({dur})", err=True)


def _candidates_from_dir(spec_dir: Path, pattern: str) -> list:
    """Load every matching *.yaml in spec_dir as a comparable TopologyCandidate.

    A `grid.yaml` (if any) is skipped here — it is handled by the grid path.
    """
    from hmm_core.selection import TopologyCandidate

    out: list = []
    for ypath in sorted(spec_dir.glob(pattern)):
        if ypath.name == "grid.yaml":
            continue
        topo = load_topology(ypath)
        out.append(TopologyCandidate(topology=topo))
    return out


def _candidates_from_grid(grid_path: Path, spec_dir: Path) -> list:
    """Build an emission x K grid of TopologyCandidates from a grid.yaml.

    grid.yaml keys: base (path to a base topology YAML, relative to spec_dir),
    k_range (list of ints), emission_types (list, default ["gaussian"]),
    n_mix (int, default 2 - used only for gmm candidates).
    """
    import yaml

    from hmm_core.selection import auto_grid

    spec = yaml.safe_load(grid_path.read_text(encoding="utf-8")) or {}
    base_ref = spec.get("base")
    if not base_ref:
        raise typer.BadParameter("grid.yaml must have a 'base' key (path to a base topology YAML)")
    base_topo = load_topology(spec_dir / base_ref)

    k_range = spec.get("k_range")
    if not k_range:
        raise typer.BadParameter("grid.yaml must have a non-empty 'k_range' list")

    emission_types = spec.get("emission_types") or ["gaussian"]
    n_mix = int(spec.get("n_mix", 2))
    return auto_grid(base_topo, list(k_range), emission_types, n_mix=n_mix)


def _print_comparison(comp, criterion: str) -> None:
    """Print a ranked, fixed-width comparison table (batch-style plain echo)."""
    best = getattr(comp, f"best_by_{criterion}")

    def fmt(v: float) -> str:
        return f"{'-':>12s}" if v != v else f"{v:>12.2f}"  # v != v catches NaN

    typer.echo(f"Model comparison (ranked by {criterion.upper()}) - best: {best or '-'}")
    typer.echo(
        f"  {'candidate':30s} {'kind':10s} "
        f"{'log_lik':>12s} {'BIC':>12s} {'AIC':>12s} {'HQIC':>12s}  note"
    )
    for c in comp.ranked(criterion):
        ok = c.comparable and c.error is None
        star = " *" if c.label == best else ""
        mark = "" if ok else " !"
        note = c.error or c.note or ""
        label = f"{c.label}{star}{mark}"
        typer.echo(
            f"  {label:30s} {c.kind:10s} "
            f"{fmt(c.log_likelihood)} {fmt(c.bic)} {fmt(c.aic)} {fmt(c.hqic)}  {note}"
        )


@app.command()
def compare(
    spec_dir: Path,
    data_path: Path,
    criterion: str = typer.Option(
        "bic", "--criterion", "-c", help="Ranking criterion: bic | aic | hqic"
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", help="Override init seed for all candidate fits"
    ),
    pattern: str = typer.Option("*.yaml", help="Glob for candidate topology files in spec_dir"),
) -> None:
    """Fit several candidate topologies on the SAME data and rank them by criterion.

    spec_dir holds one *.yaml topology per comparable candidate (Gaussian / GMM /
    Poisson - they model P(X)). Alternatively, a `grid.yaml` in spec_dir describes
    an auto-generated emission x K grid (keys: base, k_range, emission_types, n_mix).

    NHMM / Factorial candidates are NOT available via the CLI - they need explicit
    covariates / chain specs. Use the Python API (hmm_core.compare_models) for those.
    """
    from hmm_core.selection import compare_models

    if criterion not in ("bic", "aic", "hqic"):
        raise typer.BadParameter("criterion must be one of: bic, aic, hqic")

    spec_dir = spec_dir.resolve()
    if not spec_dir.exists() or not spec_dir.is_dir():
        typer.echo(f"spec_dir does not exist or is not a directory: {spec_dir}", err=True)
        raise typer.Exit(code=1)

    grid_path = spec_dir / "grid.yaml"
    if grid_path.exists():
        candidates = _candidates_from_grid(grid_path, spec_dir)
    else:
        candidates = _candidates_from_dir(spec_dir, pattern)

    if not candidates:
        typer.echo(
            f"no candidate topologies found in {spec_dir} (pattern {pattern!r})", err=True
        )
        raise typer.Exit(code=1)

    df = pd.read_csv(data_path)
    X = df.to_numpy(dtype=float)

    comp = compare_models(X, candidates, seed=(seed if seed is not None else 42))
    _print_comparison(comp, criterion)

    if getattr(comp, f"best_by_{criterion}") is None:
        typer.echo("no comparable candidate converged", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
