"""Tests for save_model / load_model / save_decoded."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from hmm_core.fit import fit
from hmm_core.io import load_model, save_decoded, save_model
from hmm_core.topology import (
    EmissionSpec,
    FitSpec,
    InitSpec,
    Topology,
)


def _topo():
    return Topology(
        name="lr3",
        n_states=3,
        state_names=["a", "b", "c"],
        emission=EmissionSpec(type="gaussian", n_features=2, covariance_type="full"),
        allowed_transitions=[("a", "a"), ("a", "b"), ("b", "b"), ("b", "c"), ("c", "c")],
        startprob="first_state",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=30, tol=1e-4),
    )


def test_save_model_writes_all_artifacts(tmp_path, synthetic_gaussian_left_right):
    result = fit(_topo(), synthetic_gaussian_left_right["X"])
    save_model(result, tmp_path)
    assert (tmp_path / "model.pkl").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "fit_log.txt").exists()


def test_summary_json_schema(tmp_path, synthetic_gaussian_left_right):
    result = fit(_topo(), synthetic_gaussian_left_right["X"])
    save_model(result, tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert "topology" in summary
    assert "fit" in summary
    assert "runtime" in summary
    for key in ("log_likelihood", "bic", "aic", "n_iter_actual", "converged",
                "mask_violation_norm"):
        assert key in summary["fit"]
    for key in ("seed", "hmmlearn_version", "hmm_core_version", "duration_seconds"):
        assert key in summary["runtime"]
    assert summary["fit"]["mask_violation_norm"] < 1e-10


def test_summary_raises_on_high_violation(tmp_path, synthetic_gaussian_left_right):
    result = fit(_topo(), synthetic_gaussian_left_right["X"])
    # Manually corrupt the transmat to inject mask violation.
    result.model.transmat_[0, 2] = 0.5
    with pytest.raises(RuntimeError, match="mask_violation"):
        save_model(result, tmp_path)


def test_load_model_roundtrip(tmp_path, synthetic_gaussian_left_right):
    original = fit(_topo(), synthetic_gaussian_left_right["X"])
    save_model(original, tmp_path)
    loaded = load_model(tmp_path / "model.pkl")
    np.testing.assert_allclose(loaded.model.transmat_, original.model.transmat_)
    np.testing.assert_allclose(loaded.model.means_, original.model.means_)
    assert loaded.log_likelihood == original.log_likelihood


def test_save_decoded_writes_parquet(tmp_path, synthetic_gaussian_left_right):
    X = synthetic_gaussian_left_right["X"]
    result = fit(_topo(), X)
    viterbi = result.model.predict(X)
    posterior = result.model.predict_proba(X)
    index = pd.RangeIndex(len(X))
    out = tmp_path / "decoded.parquet"
    save_decoded(viterbi, posterior, index, out)
    assert out.exists()
    df = pd.read_parquet(out)
    assert "viterbi" in df.columns
    assert "posterior_state_0" in df.columns
    assert "posterior_state_2" in df.columns
    assert len(df) == len(X)
