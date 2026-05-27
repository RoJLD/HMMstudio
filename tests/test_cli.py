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


def test_compare_cli_ranks_dir(runner, tmp_path, synthetic_gaussian_left_right):
    """compare fits a dir of gaussian topologies and prints a ranked table."""
    spec_dir = tmp_path / "candidates"
    spec_dir.mkdir()
    X = synthetic_gaussian_left_right["X"]
    data_csv = tmp_path / "data.csv"
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(data_csv, index=False)

    def topo_yaml(k: int) -> str:
        names = ", ".join(f"s{i}" for i in range(k))
        return f"""
name: cand_k{k}
n_states: {k}
state_names: [{names}]
emission: {{type: gaussian, covariance_type: full, n_features: 2}}
startprob: uniform
init: {{strategy: kmeans, seed: 42}}
fit: {{algorithm: baum_welch, n_iter: 15, tol: 1.0e-3}}
"""

    for k in (2, 3, 4):
        (spec_dir / f"k{k}.yaml").write_text(topo_yaml(k), encoding="utf-8")

    result = runner.invoke(app, ["compare", str(spec_dir), str(data_csv)])
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    assert "best:" in out
    assert "bic" in out
    assert "k=2" in out and "k=3" in out and "k=4" in out


def test_compare_cli_no_candidates_exits_nonzero(runner, tmp_path):
    """An empty spec_dir exits non-zero with a clear message."""
    spec_dir = tmp_path / "empty"
    spec_dir.mkdir()
    data_csv = tmp_path / "data.csv"
    pd.DataFrame({"f0": [0.1, 0.2, 0.3], "f1": [0.3, 0.4, 0.5]}).to_csv(data_csv, index=False)

    result = runner.invoke(app, ["compare", str(spec_dir), str(data_csv)])
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "no candidate" in combined.lower()


def test_compare_cli_grid_yaml(runner, tmp_path, synthetic_gaussian_left_right):
    """A grid.yaml expands a base topology into an emission x K grid."""
    spec_dir = tmp_path / "candidates"
    spec_dir.mkdir()
    X = synthetic_gaussian_left_right["X"]
    data_csv = tmp_path / "data.csv"
    pd.DataFrame(X, columns=["f0", "f1"]).to_csv(data_csv, index=False)

    base_yaml = """
name: base
n_states: 2
state_names: [s0, s1]
emission: {type: gaussian, covariance_type: full, n_features: 2}
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 15, tol: 1.0e-3}
"""
    (spec_dir / "base.yaml").write_text(base_yaml, encoding="utf-8")
    (spec_dir / "grid.yaml").write_text(
        "base: base.yaml\nk_range: [2, 3]\nemission_types: [gaussian]\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["compare", str(spec_dir), str(data_csv), "--criterion", "hqic"])
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    assert "hqic" in out
    assert "k=2" in out and "k=3" in out


def test_compare_in_app_help(runner):
    """compare is listed in the top-level --help."""
    result = runner.invoke(app, ["--help"])
    assert "compare" in result.stdout.lower()


def test_compare_help_notes_nhmm_limitation(runner):
    """compare --help mentions that NHMM / Factorial are Python-API only."""
    result = runner.invoke(app, ["compare", "--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "nhmm" in out or "factorial" in out


# ---------------------------------------------------------------------------
# Phase A.7 — `hmm-fit run --labels` (supervised + semi-supervised)
# ---------------------------------------------------------------------------


def _write_supervised_pair(
    tmp_path, states_array, *, label_col: str = "state"
) -> tuple[Path, Path]:
    """Write a (data.csv, labels.csv) pair where X is trivially state-separable.

    Returns (data_path, labels_path). Mirrors the `_well_separated_data` pattern
    used in tests/test_supervised.py — Gaussians at means {0.0, 5.0, 10.0, ...}.
    """
    import numpy as np

    rng = np.random.default_rng(0)
    centers = {k: 5.0 * float(k) for k in np.unique(states_array)}
    X = np.array([rng.normal(centers[s], 0.3) for s in states_array]).reshape(-1, 1)
    data_path = tmp_path / "data.csv"
    labels_path = tmp_path / "labels.csv"
    pd.DataFrame(X, columns=["f0"]).to_csv(data_path, index=False)
    pd.DataFrame({label_col: states_array}).to_csv(labels_path, index=False)
    return data_path, labels_path


@pytest.fixture
def _supervised_topology_yaml(tmp_path):
    """Minimal Gaussian K=3 topology with n_features=1, ergodic."""
    p = tmp_path / "topo_sup.yaml"
    p.write_text(
        """
name: cli_supervised_demo
n_states: 3
state_names: [low, mid, high]
emission: {type: gaussian, covariance_type: diag, n_features: 1}
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 50, tol: 1.0e-3}
""",
        encoding="utf-8",
    )
    return p


def test_run_with_labels_dispatches_to_supervised(runner, tmp_path, _supervised_topology_yaml):
    """`hmm-fit run --labels states.csv` writes a fit whose `n_iter_actual == 1`
    (the closed-form supervised signature — Baum-Welch would iterate)."""
    import json

    import numpy as np

    states = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 0, 1, 2, 0, 1, 2, 2, 2, 0, 1, 1])
    data_path, labels_path = _write_supervised_pair(tmp_path, states)

    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "run",
            str(_supervised_topology_yaml),
            str(data_path),
            "--labels",
            str(labels_path),
            "--output",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.stdout
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    # Supervised closed-form MLE = one pass, deterministic
    assert summary["fit"]["n_iter_actual"] == 1
    assert summary["fit"]["converged"] is True


def test_run_with_labels_csv_must_have_single_column(runner, tmp_path, _supervised_topology_yaml):
    """A multi-column labels CSV is ambiguous → BadParameter."""
    import numpy as np

    states = np.array([0, 1, 2, 0, 1, 2])
    data_path, _ = _write_supervised_pair(tmp_path, states)

    bad_labels = tmp_path / "labels_bad.csv"
    pd.DataFrame({"state": states, "extra": np.zeros_like(states)}).to_csv(bad_labels, index=False)

    result = runner.invoke(
        app,
        [
            "run",
            str(_supervised_topology_yaml),
            str(data_path),
            "--labels",
            str(bad_labels),
            "--output",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code != 0
    # typer.BadParameter renders to stderr ; click.exceptions.UsageError stays
    # on the Result.output (which CliRunner merges stdout+stderr by default).
    combined = (result.output or "") + str(result.exception or "")
    assert "single" in combined.lower() or "column" in combined.lower()


def test_run_with_labels_semi_supervised_via_minus_one(runner, tmp_path, _supervised_topology_yaml):
    """An int labels CSV with -1 sentinels for unlabelled positions dispatches
    to semi-supervised EM (not closed-form). We just check the run succeeds
    and the fit completes — convergence may need >1 iteration."""
    import numpy as np

    # 30 obs : 15 labelled, 15 with -1 sentinel
    base = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 0, 1, 2, 0, 1, 2])
    states_full = np.array(list(base) + [-1] * 15)
    rng = np.random.default_rng(0)
    centers = {0: 0.0, 1: 5.0, 2: 10.0}
    # Use the original (labelled-only) base for sampling the unlabelled tail
    full_seq = np.array(list(base) + list(rng.choice([0, 1, 2], size=15)))
    X = np.array([rng.normal(centers[s], 0.3) for s in full_seq]).reshape(-1, 1)

    data_path = tmp_path / "data.csv"
    labels_path = tmp_path / "labels.csv"
    pd.DataFrame(X, columns=["f0"]).to_csv(data_path, index=False)
    pd.DataFrame({"state": states_full}).to_csv(labels_path, index=False)

    result = runner.invoke(
        app,
        [
            "run",
            str(_supervised_topology_yaml),
            str(data_path),
            "--labels",
            str(labels_path),
            "--output",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 0, result.stdout


def test_run_help_documents_labels(runner):
    """`hmm-fit run --help` lists --labels and mentions supervised."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--labels" in result.stdout
    out = result.stdout.lower()
    assert "supervised" in out or "label" in out
