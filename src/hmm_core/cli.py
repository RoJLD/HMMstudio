"""hmm-fit CLI: validate / run / decode / show."""

from __future__ import annotations

from pathlib import Path

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


if __name__ == "__main__":
    app()
