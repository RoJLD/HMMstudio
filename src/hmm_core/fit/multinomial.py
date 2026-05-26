"""Constrained Multinomial (Categorical) HMM."""

from __future__ import annotations

import numpy as np
from hmmlearn.hmm import CategoricalHMM

from hmm_core.fit._base import (
    _apply_label_clamp,
    _apply_mask,
    _map_update,
    _resolve_clamp_slice,
    _smooth_startprob_,
)


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
        if transmat_prior is not None:
            self.transmat_prior = transmat_prior

    def _do_mstep(self, stats):
        super()._do_mstep(stats)
        if self.transmat_prior is not None and self.transmat_mask is not None:
            self.transmat_ = _map_update(self.transmat_, self.transmat_prior, self.transmat_mask)
        if self.transmat_mask is not None:
            self.transmat_ = _apply_mask(self.transmat_, self.transmat_mask)
        _smooth_startprob_(self)

    def _estep_begin(self):
        cursor = getattr(self, "_label_clamp_cursor", None)
        if cursor is not None:
            cursor[0] = 0
        super()._estep_begin()

    def _compute_log_likelihood(self, X):
        log_prob = super()._compute_log_likelihood(X)
        clamp = getattr(self, "_label_clamp", None)
        if clamp is not None:
            seg = _resolve_clamp_slice(
                clamp,
                getattr(self, "_label_clamp_segments", None),
                getattr(self, "_label_clamp_cursor", [0]),
                log_prob.shape[0],
            )
            log_prob = _apply_label_clamp(log_prob, seg)
        return log_prob
