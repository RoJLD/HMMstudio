"""IO: load topology YAML, save/load fitted models and decoded outputs."""

from __future__ import annotations

from pathlib import Path

import yaml

from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def load_topology(path: str | Path) -> Topology:
    """Load and validate a Topology from a YAML file.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    TopologyError
        If the file content fails Topology.validate().
    yaml.YAMLError
        If the file is not valid YAML.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"topology file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    e = raw["emission"]
    emission = EmissionSpec(
        type=e["type"],
        n_features=e.get("n_features"),
        covariance_type=e.get("covariance_type"),
        n_mix=e.get("n_mix"),
        n_symbols=e.get("n_symbols"),
    )
    init = InitSpec(strategy=raw["init"]["strategy"], seed=int(raw["init"]["seed"]))
    fit = FitSpec(
        algorithm=raw["fit"]["algorithm"],
        n_iter=int(raw["fit"]["n_iter"]),
        tol=float(raw["fit"]["tol"]),
    )
    allowed = raw.get("allowed_transitions")
    if allowed is not None:
        allowed = [tuple(pair) for pair in allowed]

    topo = Topology(
        name=raw["name"],
        n_states=int(raw["n_states"]),
        state_names=list(raw["state_names"]),
        emission=emission,
        allowed_transitions=allowed,
        startprob=raw["startprob"],
        init=init,
        fit=fit,
    )
    topo.validate()
    return topo
