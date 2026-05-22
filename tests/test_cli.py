"""Smoke tests for the hmm-fit CLI via typer.testing.CliRunner."""

from __future__ import annotations

from pathlib import Path

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
        csv_path,
        index=False,
    )
    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "run",
            str(FIXTURES / "topology_valid_gaussian.yaml"),
            str(csv_path),
            "--output",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "model.pkl").exists()
    assert (out_dir / "summary.json").exists()


def test_show_prints_summary(runner, tmp_path, synthetic_gaussian_left_right):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(synthetic_gaussian_left_right["X"], columns=["f0", "f1"]).to_csv(
        csv_path,
        index=False,
    )
    out_dir = tmp_path / "out"
    runner.invoke(
        app,
        [
            "run",
            str(FIXTURES / "topology_valid_gaussian.yaml"),
            str(csv_path),
            "--output",
            str(out_dir),
        ],
    )
    result = runner.invoke(app, ["show", str(out_dir / "model.pkl")])
    assert result.exit_code == 0
    assert "log_likelihood" in result.stdout.lower() or "log lik" in result.stdout.lower()
    assert "bic" in result.stdout.lower()


def test_decode_writes_parquet(runner, tmp_path, synthetic_gaussian_left_right):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(synthetic_gaussian_left_right["X"], columns=["f0", "f1"]).to_csv(
        csv_path,
        index=False,
    )
    out_dir = tmp_path / "out"
    runner.invoke(
        app,
        [
            "run",
            str(FIXTURES / "topology_valid_gaussian.yaml"),
            str(csv_path),
            "--output",
            str(out_dir),
        ],
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


def test_batch_runs_multiple_jobs(runner, tmp_path, synthetic_gaussian_left_right):
    """Batch processes multiple (yaml, csv) pairs in parallel."""
    import pandas as pd

    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    X = synthetic_gaussian_left_right["X"]
    df = pd.DataFrame(X, columns=["f0", "f1"])

    topology_yaml = """
name: batch_test
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 15, tol: 1.0e-3}
"""

    # Create 3 (yaml, csv) pairs
    for stem in ["job_001", "job_002", "job_003"]:
        (input_dir / f"{stem}.yaml").write_text(topology_yaml, encoding="utf-8")
        df.to_csv(input_dir / f"{stem}.csv", index=False)

    result = runner.invoke(
        app,
        ["batch", str(input_dir), "--output", str(output_dir), "--workers", "2"],
    )
    assert result.exit_code == 0, result.stdout
    # All 3 outputs exist
    for stem in ["job_001", "job_002", "job_003"]:
        assert (output_dir / stem / "model.pkl").exists()
        assert (output_dir / stem / "summary.json").exists()


def test_batch_skips_unpaired_yamls(runner, tmp_path, synthetic_gaussian_left_right):
    """A YAML without a matching CSV is reported but not fatal."""
    import pandas as pd

    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    X = synthetic_gaussian_left_right["X"]
    df = pd.DataFrame(X, columns=["f0", "f1"])

    topology_yaml = """
name: t
n_states: 3
state_names: [a, b, c]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 10, tol: 1.0e-3}
"""

    # One paired job + one orphan yaml
    (input_dir / "paired.yaml").write_text(topology_yaml, encoding="utf-8")
    df.to_csv(input_dir / "paired.csv", index=False)
    (input_dir / "orphan.yaml").write_text(topology_yaml, encoding="utf-8")
    # NO orphan.csv

    result = runner.invoke(
        app,
        ["batch", str(input_dir), "--output", str(output_dir)],
    )
    assert result.exit_code == 0, result.stdout
    assert (output_dir / "paired" / "model.pkl").exists()
    assert not (output_dir / "orphan").exists()


def test_batch_fails_on_invalid_topology(runner, tmp_path, synthetic_gaussian_left_right):
    """If a job's topology is invalid, batch reports failure and exits 1."""
    import pandas as pd

    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    X = synthetic_gaussian_left_right["X"]
    df = pd.DataFrame(X, columns=["f0", "f1"])

    bad_yaml = "not: a valid: topology"
    (input_dir / "bad.yaml").write_text(bad_yaml, encoding="utf-8")
    df.to_csv(input_dir / "bad.csv", index=False)

    result = runner.invoke(
        app,
        ["batch", str(input_dir), "--output", str(output_dir)],
    )
    assert result.exit_code == 1
    assert "failed" in result.stdout.lower() or "failed" in (result.stderr or "").lower()


def test_batch_empty_input_dir(runner, tmp_path):
    """An empty input directory exits cleanly with a clear message."""
    input_dir = tmp_path / "empty"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        ["batch", str(input_dir), "--output", str(output_dir)],
    )
    assert result.exit_code == 1
    # "no valid" appears in the error message
    combined = (result.stdout or "") + (result.stderr or "")
    assert "no valid" in combined.lower() or "0" in combined


def test_batch_help(runner):
    """The CLI surfaces the batch command in --help."""
    result = runner.invoke(app, ["--help"])
    assert "batch" in result.stdout.lower()
