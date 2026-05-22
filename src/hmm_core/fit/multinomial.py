"""Constrained Multinomial (Categorical) HMM."""

from __future__ import annotations

import numpy as np
from hmmlearn.hmm import CategoricalHMM

from hmm_core.fit._base import _apply_mask, _map_update


class ConstrainedMultinomialHMM(CategoricalHMM):
    """CategoricalHMM with optional binary mask enforced on transmat_ post M-step.

    The public name "Multinomial" is preserved for users (topology YAML uses
    ``emission.type: multinomial``) even though we wrap ``CategoricalHMM``
    from hmmlearn>=0.3 (the API was renamed).

    Parameters
    ----------
    transmat_mask : K x K boolean array, or None
        Edges where ``mask`` is False are forced to 0 after each M-step
        (and renormalized). When None, behaves identically to hmmlearn
        ``CategoricalHMM``.
    transmat_prior : K x K float array, or None
        Dirichlet prior pseudo-counts. When provided, MAP smoothing is applied
        before mask enforcement at each M-step. None = MLE (no prior).
    """

    def __init__(
        self,
        *args,
        transmat_mask: np.ndarray | None = None,
        transmat_prior: np.ndarray | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.transmat_mask = transmat_mask
        self.transmat_prior = transmat_prior

    def _do_mstep(self, stats):
        super()._do_mstep(stats)
        if self.transmat_prior is not None and self.transmat_mask is not None:
            self.transmat_ = _map_update(self.transmat_, self.transmat_prior, self.transmat_mask)
        if self.transmat_mask is not None:
            self.transmat_ = _apply_mask(self.transmat_, self.transmat_mask)
