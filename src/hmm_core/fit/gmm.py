"""Constrained GMM HMM."""

from __future__ import annotations

import numpy as np
from hmmlearn.hmm import GMMHMM

from hmm_core.fit._base import _apply_mask


class ConstrainedGMMHMM(GMMHMM):
    """GMMHMM with optional binary mask enforced on transmat_ after each M-step."""

    def __init__(self, *args, transmat_mask: np.ndarray | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transmat_mask = transmat_mask

    def _do_mstep(self, stats):
        super()._do_mstep(stats)
        if self.transmat_mask is not None:
            self.transmat_ = _apply_mask(self.transmat_, self.transmat_mask)
