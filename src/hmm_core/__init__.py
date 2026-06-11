"""hmm-core: constrained Baum-Welch fit + topology authoring for HMMs."""

__version__ = "1.1.0"

from hmm_core.export_graph import (
    export_activations,
    export_model_graph,
    save_model_graph,
)
from hmm_core.features import FeatureSelectionResult, unsupervised_feature_selection
from hmm_core.fit import FittedModel, fit
from hmm_core.gmm_nhmm import GMMNHMMFittedModel, fit_gmm_nhmm
from hmm_core.io import load_model, load_topology, save_decoded, save_model
from hmm_core.nhmm import NHMMFittedModel, fit_nhmm
from hmm_core.regimes import regime_labels, regime_order_by_feature_mean
from hmm_core.selection import (
    Candidate,
    CandidateResult,
    FactorialCandidate,
    ModelComparison,
    NHMMCandidate,
    TopologyCandidate,
    auto_grid,
    compare_models,
)
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
    TopologyError,
)

__all__ = [
    "Candidate",
    "CandidateResult",
    "EmissionSpec",
    "FactorialCandidate",
    "FeatureSelectionResult",
    "FitSpec",
    "FittedModel",
    "GMMNHMMFittedModel",
    "InitSpec",
    "ModelComparison",
    "NHMMCandidate",
    "NHMMFittedModel",
    "Topology",
    "TopologyCandidate",
    "TopologyError",
    "auto_grid",
    "compare_models",
    "export_activations",
    "export_model_graph",
    "save_model_graph",
    "fit",
    "fit_gmm_nhmm",
    "fit_nhmm",
    "load_model",
    "load_topology",
    "regime_labels",
    "regime_order_by_feature_mean",
    "save_decoded",
    "save_model",
    "unsupervised_feature_selection",
]
