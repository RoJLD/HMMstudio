"""hmm-core: constrained Baum-Welch fit + topology authoring for HMMs."""

__version__ = "0.2.0"  # bumped: NHMM added

from hmm_core.fit import FittedModel, fit
from hmm_core.io import load_model, load_topology, save_decoded, save_model
from hmm_core.nhmm import NHMMFittedModel, fit_nhmm
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)

__all__ = [
    "EmissionSpec",
    "FitSpec",
    "FittedModel",
    "InitSpec",
    "NHMMFittedModel",
    "Topology",
    "TopologyError",
    "fit",
    "fit_nhmm",
    "load_model",
    "load_topology",
    "save_decoded",
    "save_model",
]
