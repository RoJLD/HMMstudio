"""Constrained Poisson HMM."""

from __future__ import annotations

import numpy as np
from hmmlearn.hmm import PoissonHMM

from hmm_core.fit._base import _apply_mask


class ConstrainedPoissonHMM(PoissonHMM):
    """PoissonHMM with optional binary mask enforced on transmat_ post M-step."""

    def __init__(self, *args, transmat_mask: np.ndarray | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transmat_mask = transmat_mask

    def _do_mstep(self, stats):
        super()._do_mstep(stats)
        if self.transmat_mask is not None:
            self.transmat_ = _apply_mask(self.transmat_, self.transmat_mask)
