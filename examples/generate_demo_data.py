"""Generate examples/data_gaussian.csv — a synthetic Gaussian-HMM trajectory.

Run from repo root: python examples/generate_demo_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def main():
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


if __name__ == "__main__":
    main()
