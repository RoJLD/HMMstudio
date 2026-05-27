"""Generate synthetic example datasets shipped with the repo.

Run from repo root: ``python examples/generate_demo_data.py``

Outputs (overwrites existing files):

* ``examples/data_gaussian.csv`` — 2-feature Gaussian-HMM trajectory used by
  the README quickstart and most CLI smoke tests.
* ``examples/data_supervised.csv`` + ``examples/states_supervised.csv``
  + ``examples/states_semi_supervised.csv`` — a 1-feature 3-state trajectory
  for the supervised / semi-supervised CLI examples (Phase A.7).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _write_gaussian_4state():
    A = np.array([[0.85, 0.15, 0.00, 0.00],
                  [0.00, 0.80, 0.20, 0.00],
                  [0.05, 0.00, 0.80, 0.15],
                  [0.30, 0.00, 0.00, 0.70]])
    means = np.array([[ 0.0,  0.0],
                      [ 2.0,  1.5],
                      [ 0.0, -3.0],
                      [-3.0, -3.0]])
    cov = 0.4 * np.eye(2)
    rng = np.random.default_rng(2026)
    n = 2000
    X = np.zeros((n, 2))
    state = 0
    for t in range(n):
        X[t] = rng.multivariate_normal(means[state], cov)
        state = int(rng.choice(4, p=A[state]))
    out = Path(__file__).parent / "data_gaussian.csv"
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(out, index=False)
    print(f"wrote {out} ({n} rows)")


def _write_supervised_3state():
    """Generate the supervised / semi-supervised example bundle (Phase A.7)."""
    A = np.array([
        [0.85, 0.15, 0.00],
        [0.05, 0.80, 0.15],
        [0.00, 0.10, 0.90],
    ])
    means = np.array([0.0, 5.0, 10.0])         # trivially separable Gaussians
    sigma = 0.6
    rng = np.random.default_rng(2027)
    n = 600
    states = np.zeros(n, dtype=int)
    state = 0
    for t in range(n):
        states[t] = state
        state = int(rng.choice(3, p=A[state]))
    X = rng.normal(means[states], sigma).reshape(-1, 1)

    here = Path(__file__).parent
    data_path = here / "data_supervised.csv"
    sup_labels = here / "states_supervised.csv"
    semi_labels = here / "states_semi_supervised.csv"

    pd.DataFrame(X, columns=["f0"]).to_csv(data_path, index=False)
    pd.DataFrame({"state": states}).to_csv(sup_labels, index=False)

    # Semi-supervised variant : keep the first third labelled, mask the rest
    # with the -1 sentinel. The fitter clamps the labelled portion and runs
    # constrained Baum-Welch on the unlabelled tail.
    masked = states.copy()
    cut = n // 3
    masked[cut:] = -1
    pd.DataFrame({"state": masked}).to_csv(semi_labels, index=False)

    print(f"wrote {data_path} ({n} rows)")
    print(f"wrote {sup_labels} (fully labelled)")
    print(f"wrote {semi_labels} ({cut} labelled / {n - cut} unlabelled with -1)")


def main():
    _write_gaussian_4state()
    _write_supervised_3state()


if __name__ == "__main__":
    main()
