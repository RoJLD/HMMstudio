"""IO: load topology YAML, save/load fitted models and decoded outputs."""

from __future__ import annotations

import json
import pickle
import warnings
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hmm_core.fit import FittedModel

import hmmlearn
import numpy as np
import pandas as pd
import yaml

from hmm_core import __version__ as _PKG_VERSION
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)


def load_topology(path: str | Path) -> Topology:
    """Load and validate a Topology from a YAML file.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    TopologyError
        If the file content is malformed (empty, not a YAML mapping,
        missing required keys) or fails Topology.validate().
    yaml.YAMLError
        If the file is not valid YAML.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"topology file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TopologyError(f"topology file at {p} is empty or not a YAML mapping")

    try:
        e = raw["emission"]
        emission = EmissionSpec(
            type=e["type"],
            n_features=e.get("n_features"),
            covariance_type=e.get("covariance_type"),
            n_mix=e.get("n_mix"),
            n_symbols=e.get("n_symbols"),
        )
        init = InitSpec(
            strategy=raw["init"]["strategy"],
            seed=int(raw["init"]["seed"]),
        )
        fit = FitSpec(
            algorithm=raw["fit"]["algorithm"],
            n_iter=int(raw["fit"]["n_iter"]),
            tol=float(raw["fit"]["tol"]),
        )
        allowed = raw.get("allowed_transitions")
        if allowed is not None:
            allowed = [tuple(pair) for pair in allowed]

        emissions = None
        if raw.get("emissions"):
            emissions = []
            for e_raw in raw["emissions"]:
                emissions.append(
                    EmissionSpec(
                        type=e_raw.get("type", emission.type),
                        n_features=e_raw.get("n_features", emission.n_features),
                        covariance_type=e_raw.get("covariance_type", emission.covariance_type),
                        n_mix=e_raw.get("n_mix", emission.n_mix),
                        n_symbols=e_raw.get("n_symbols", emission.n_symbols),
                        init_mean=e_raw.get("init_mean"),
                        init_covar=e_raw.get("init_covar"),
                        init_lambda=e_raw.get("init_lambda"),
                        init_emissionprob=e_raw.get("init_emissionprob"),
                    )
                )

        topo = Topology(
            name=raw["name"],
            n_states=int(raw["n_states"]),
            state_names=list(raw["state_names"]),
            emission=emission,
            allowed_transitions=allowed,
            startprob=raw["startprob"],
            init=init,
            fit=fit,
            emissions=emissions,
        )
    except KeyError as exc:
        raise TopologyError(f"missing required field: {exc}") from exc

    topo.validate()
    return topo


def _topology_to_dict(topology: Topology) -> dict:
    """Convert Topology to a JSON-serializable dict (allowed_transitions as lists)."""
    d = asdict(topology)
    if d["allowed_transitions"] is not None:
        d["allowed_transitions"] = [list(t) for t in d["allowed_transitions"]]
    return d


def save_model(fitted, output_dir: str | Path) -> None:
    """Write model.pkl, summary.json, fit_log.txt to output_dir.

    Raises
    ------
    RuntimeError
        If the model's mask_violation_norm exceeds 1e-10 (sanity check that
        the constrained M-step actually worked).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    mask = fitted.topology.transition_mask()
    violation = float((fitted.model.transmat_ * (~mask)).sum())
    if violation >= 1e-10:
        raise RuntimeError(
            f"mask_violation_norm={violation:.3e} exceeds 1e-10 — fit did not respect topology"
        )

    with (out / "model.pkl").open("wb") as f:
        pickle.dump(fitted, f, protocol=pickle.HIGHEST_PROTOCOL)

    summary = {
        "schema_version": 1,
        "topology": _topology_to_dict(fitted.topology),
        "fit": {
            "log_likelihood": fitted.log_likelihood,
            "bic": fitted.bic,
            "aic": fitted.aic,
            "n_iter_actual": fitted.n_iter_actual,
            "converged": fitted.converged,
            "mask_violation_norm": violation,
        },
        "runtime": {
            "seed": fitted.seed,
            "hmmlearn_version": hmmlearn.__version__,
            "hmm_core_version": _PKG_VERSION,
            "duration_seconds": fitted.duration_seconds,
        },
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, default=float), encoding="utf-8"
    )

    monitor = getattr(fitted.model, "monitor_", None)
    history = getattr(monitor, "history", []) if monitor is not None else []
    lines = ["iter\tlog_likelihood"] + [f"{i}\t{ll:.6f}" for i, ll in enumerate(history)]
    (out / "fit_log.txt").write_text("\n".join(lines), encoding="utf-8")


def load_model(path: str | Path) -> "FittedModel":
    """Unpickle a FittedModel. Warn if hmmlearn version mismatches the saved one."""
    p = Path(path)
    with p.open("rb") as f:
        fitted = pickle.load(f)
    summary_path = p.parent / "summary.json"
    if summary_path.exists():
        saved_version = json.loads(summary_path.read_text(encoding="utf-8"))["runtime"][
            "hmmlearn_version"
        ]
        if saved_version != hmmlearn.__version__:
            warnings.warn(
                f"hmmlearn version mismatch: saved={saved_version}, current={hmmlearn.__version__}",
                stacklevel=2,
            )
    return fitted


def save_decoded(
    viterbi: np.ndarray,
    posterior: np.ndarray,
    index: pd.Index,
    output: str | Path,
) -> None:
    """Write (index + viterbi + posterior_state_k columns) as parquet."""
    df = pd.DataFrame({"viterbi": viterbi}, index=index)
    K = posterior.shape[1]
    for k in range(K):
        df[f"posterior_state_{k}"] = posterior[:, k]
    df.to_parquet(output)
