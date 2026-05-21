"""End-to-end smoke test using the examples/ fixtures.

Verifies the full path: load YAML -> fit -> save -> load -> decode -> re-save.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from hmm_core.fit import fit
from hmm_core.io import load_model, load_topology, save_decoded, save_model

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_full_pipeline(tmp_path):
    topo = load_topology(EXAMPLES / "topology_left_right.yaml")
    df = pd.read_csv(EXAMPLES / "data_gaussian.csv")
    X = df.to_numpy(dtype=float)

    result = fit(topo, X)

    # Mask is honored.
    mask = topo.transition_mask()
    assert (result.model.transmat_ * (~mask)).sum() < 1e-10

    # Forbidden edges are literally zero.
    assert result.model.transmat_[0, 2] == 0.0
    assert result.model.transmat_[1, 3] == 0.0
    assert result.model.transmat_[3, 1] == 0.0

    # Save + load roundtrip.
    out_dir = tmp_path / "demo_out"
    save_model(result, out_dir)
    loaded = load_model(out_dir / "model.pkl")
    np.testing.assert_allclose(loaded.model.transmat_, result.model.transmat_)

    # Decode roundtrip.
    viterbi = loaded.model.predict(X)
    posterior = loaded.model.predict_proba(X)
    decoded_path = tmp_path / "decoded.parquet"
    save_decoded(viterbi, posterior, pd.RangeIndex(len(X)), decoded_path)
    loaded_decoded = pd.read_parquet(decoded_path)
    assert len(loaded_decoded) == len(X)
    assert (loaded_decoded["viterbi"] == viterbi).all()
