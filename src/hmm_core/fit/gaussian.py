"""Constrained Gaussian HMM: subclass with masked _do_mstep."""

from __future__ import annotations

import numpy as np
from hmmlearn.hmm import GaussianHMM

from hmm_core.fit._base import _apply_mask


class ConstrainedGaussianHMM(GaussianHMM):
    """GaussianHMM with optional binary mask enforced on transmat_ after each M-step.

    Parameters
    ----------
    transmat_mask : K x K boolean array, or None
        Edges where ``mask`` is False are forced to 0 after each M-step
        (and renormalized). When None, behaves identically to hmmlearn
        ``GaussianHMM``.
    """

    def __init__(self, *args, transmat_mask: np.ndarray | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transmat_mask = transmat_mask

    def _do_mstep(self, stats):
        super()._do_mstep(stats)
        if self.transmat_mask is not None:
            self.transmat_ = _apply_mask(self.transmat_, self.transmat_mask)
