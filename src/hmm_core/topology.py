"""Topology declaration: states, transitions, emission spec, init/fit hyperparams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


class TopologyError(ValueError):
    """Raised when a Topology fails validation."""


@dataclass(frozen=True)
class EmissionSpec:
    type: Literal["gaussian", "gmm", "multinomial", "poisson"]
    n_features: int | None = None
    covariance_type: str | None = None
    n_mix: int | None = None
    n_symbols: int | None = None


@dataclass(frozen=True)
class InitSpec:
    strategy: Literal["uniform", "random", "kmeans", "data_frequencies"]
    seed: int


@dataclass(frozen=True)
class FitSpec:
    algorithm: Literal["baum_welch"]
    n_iter: int
    tol: float


@dataclass(frozen=True)
class Topology:
    name: str
    n_states: int
    state_names: list[str]
    emission: EmissionSpec
    allowed_transitions: list[tuple[str, str]] | None
    startprob: str | list[float]
    init: InitSpec
    fit: FitSpec

    def validate(self) -> None:
        if len(self.state_names) != self.n_states:
            raise TopologyError(
                f"state_names has length {len(self.state_names)} but n_states={self.n_states}"
            )
        if len(set(self.state_names)) != len(self.state_names):
            raise TopologyError("state_names must be unique")

        if self.allowed_transitions is not None:
            known = set(self.state_names)
            for src, dst in self.allowed_transitions:
                if src not in known:
                    raise TopologyError(f"unknown state '{src}' in allowed_transitions")
                if dst not in known:
                    raise TopologyError(f"unknown state '{dst}' in allowed_transitions")

        e = self.emission
        if e.type in ("gaussian", "gmm"):
            if e.n_features is None or e.n_features < 1:
                raise TopologyError(f"emission.n_features must be a positive int for {e.type}")
            if e.covariance_type not in ("full", "diag", "tied", "spherical"):
                raise TopologyError(
                    f"emission.covariance_type must be full/diag/tied/spherical for {e.type}"
                )
            if e.type == "gmm" and (e.n_mix is None or e.n_mix < 1):
                raise TopologyError("emission.n_mix must be a positive int for gmm")
        elif e.type == "multinomial":
            if e.n_symbols is None or e.n_symbols < 2:
                raise TopologyError("emission.n_symbols must be >= 2 for multinomial")
        elif e.type == "poisson":
            if e.n_features is None or e.n_features < 1:
                raise TopologyError("emission.n_features must be a positive int for poisson")
        else:
            raise TopologyError(f"unknown emission.type {e.type!r}")

        if isinstance(self.startprob, list):
            if len(self.startprob) != self.n_states:
                raise TopologyError(
                    f"startprob list has length {len(self.startprob)} but n_states={self.n_states}"
                )
            if abs(sum(self.startprob) - 1.0) > 1e-6:
                raise TopologyError("startprob values must sum to 1")
        elif self.startprob not in ("uniform", "first_state"):
            raise TopologyError(
                f"startprob must be 'uniform', 'first_state', or a list of {self.n_states} floats"
            )

    def transition_mask(self) -> np.ndarray:
        K = self.n_states
        if self.allowed_transitions is None:
            return np.ones((K, K), dtype=bool)
        index = {name: i for i, name in enumerate(self.state_names)}
        mask = np.zeros((K, K), dtype=bool)
        for src, dst in self.allowed_transitions:
            mask[index[src], index[dst]] = True
        return mask
