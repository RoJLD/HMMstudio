"""hmm-core: constrained Baum-Welch fit + topology authoring for HMMs."""

__version__ = "1.1.0"

from hmm_core.fit import FittedModel, fit
from hmm_core.gmm_nhmm import GMMNHMMFittedModel, fit_gmm_nhmm
from hmm_core.io import load_model, load_topology, save_decoded, save_model
from hmm_core.nhmm import NHMMFittedModel, fit_nhmm
from hmm_core.regimes import regime_labels, regime_order_by_feature_mean
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
    "GMMNHMMFittedModel",
    "InitSpec",
    "NHMMFittedModel",
    "Topology",
    "TopologyError",
    "fit",
    "fit_gmm_nhmm",
    "fit_nhmm",
    "load_model",
    "load_topology",
    "regime_labels",
    "regime_order_by_feature_mean",
    "save_decoded",
    "save_model",
]
