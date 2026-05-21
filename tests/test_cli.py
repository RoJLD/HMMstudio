"""Smoke tests for the hmm-fit CLI via typer.testing.CliRunner."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from hmm_core.cli import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def runner():
    return CliRunner()


def test_validate_ok(runner):
    result = runner.invoke(app, ["validate", str(FIXTURES / "topology_valid_gaussian.yaml")])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_fails_on_bad_file(runner, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
name: bad
n_states: 3
state_names: [a, b]
emission: {type: gaussian, covariance_type: full, n_features: 1}
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-4}
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", str(bad)])
    assert result.exit_code != 0


def test_run_writes_outputs(runner, tmp_path, synthetic_gaussian_left_right):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(synthetic_gaussian_left_right["X"], columns=["f0", "f1"]).to_csv(
        csv_path, index=False,
    )
    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        ["run", str(FIXTURES / "topology_valid_gaussian.yaml"), str(csv_path),
         "--output", str(out_dir)],
    )
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "model.pkl").exists()
    assert (out_dir / "summary.json").exists()


def test_show_prints_summary(runner, tmp_path, synthetic_gaussian_left_right):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(synthetic_gaussian_left_right["X"], columns=["f0", "f1"]).to_csv(
        csv_path, index=False,
    )
    out_dir = tmp_path / "out"
    runner.invoke(
        app,
        ["run", str(FIXTURES / "topology_valid_gaussian.yaml"), str(csv_path),
         "--output", str(out_dir)],
    )
    result = runner.invoke(app, ["show", str(out_dir / "model.pkl")])
    assert result.exit_code == 0
    assert "log_likelihood" in result.stdout.lower() or "log lik" in result.stdout.lower()
    assert "bic" in result.stdout.lower()


def test_decode_writes_parquet(runner, tmp_path, synthetic_gaussian_left_right):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(synthetic_gaussian_left_right["X"], columns=["f0", "f1"]).to_csv(
        csv_path, index=False,
    )
    out_dir = tmp_path / "out"
    runner.invoke(
        app,
        ["run", str(FIXTURES / "topology_valid_gaussian.yaml"), str(csv_path),
         "--output", str(out_dir)],
    )
    decoded_path = tmp_path / "decoded.parquet"
    result = runner.invoke(
        app,
        ["decode", str(out_dir / "model.pkl"), str(csv_path), "--output", str(decoded_path)],
    )
    assert result.exit_code == 0
    df = pd.read_parquet(decoded_path)
    assert "viterbi" in df.columns
    assert len(df) == len(synthetic_gaussian_left_right["X"])
