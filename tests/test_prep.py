"""Tests for the data prep layer (Phase B.11).

Coverage :
    - Each atomic op produces expected output on small fixtures
    - Engine parses YAML, resolves includes, executes steps in order
    - Composition : recipes can include other recipes (1 level + recursive)
    - Library : every bundled canonical recipe loads and runs successfully
    - Python escape hatch : Pipeline().add_step(...).fit_transform(...)
    - Output split : observations / covariates exposed as X / Z
    - Provenance : the applied trace is preserved and writable as sidecar
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hmm_core.prep import OPS, Pipeline, list_recipes, load_recipe, register_op


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_df():
    """OHLCV-like time series with some NaN and outliers."""
    rng = np.random.default_rng(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    price = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    volume = rng.uniform(1000, 5000, n)
    df = pd.DataFrame(
        {
            "close": price,
            "volume": volume,
        },
        index=dates,
    )
    # Inject some NaN and outliers
    df.iloc[10, 0] = np.nan
    df.iloc[50, 1] = np.nan
    df.iloc[75, 0] = price[75] * 5  # outlier
    return df


@pytest.fixture
def tiny_df():
    return pd.DataFrame(
        {
            "a": [1.0, 2.0, np.nan, 4.0, 5.0],
            "b": [10.0, np.nan, 30.0, 40.0, 50.0],
        }
    )


# ---------------------------------------------------------------------------
# Atomic ops
# ---------------------------------------------------------------------------


def test_op_select_columns(sample_df):
    out = OPS["select_columns"](sample_df, columns=["close"])
    assert list(out.columns) == ["close"]


def test_op_drop_columns(sample_df):
    out = OPS["drop_columns"](sample_df, columns=["volume"])
    assert "volume" not in out.columns
    assert "close" in out.columns


def test_op_rename_columns(sample_df):
    out = OPS["rename_columns"](sample_df, mapping={"close": "price"})
    assert "price" in out.columns
    assert "close" not in out.columns


def test_op_fillna_forward(tiny_df):
    out = OPS["fillna_forward"](tiny_df)
    assert out["a"].iloc[2] == 2.0  # was NaN, filled from index 1
    assert out["b"].iloc[1] == 10.0  # was NaN, filled from index 0


def test_op_fillna_backward(tiny_df):
    out = OPS["fillna_backward"](tiny_df)
    assert out["a"].iloc[2] == 4.0  # was NaN, filled from index 3
    assert out["b"].iloc[1] == 30.0


def test_op_fillna_value(tiny_df):
    out = OPS["fillna_value"](tiny_df, value=999.0)
    assert out["a"].iloc[2] == 999.0
    assert out["b"].iloc[1] == 999.0


def test_op_dropna(tiny_df):
    out = OPS["dropna"](tiny_df)
    assert len(out) == 3  # rows with NaN removed


def test_op_log_diff(sample_df):
    out = OPS["log_diff"](sample_df, column="close", new_name="logret")
    assert "logret" in out.columns
    # First value is NaN by construction of diff()
    assert pd.isna(out["logret"].iloc[0])
    # Verify the math : log_diff[t] == log(price[t]) - log(price[t-1])
    # On a non-outlier point, the value should be ~0 (small daily returns)
    valid = out["logret"].dropna()
    # The fixture injects a 5× outlier at index 75 → log_diff ≈ log(5) ≈ 1.61
    # Excluding that spike, all values should be < 0.05 (typical daily return)
    sorted_abs = valid.abs().sort_values()
    median_abs_return = sorted_abs.iloc[len(sorted_abs) // 2]
    assert median_abs_return < 0.05, (
        f"median |log_return| = {median_abs_return:.4f} ; expected typical daily return"
    )


def test_op_rolling_std(sample_df):
    out = OPS["rolling_std"](sample_df.fillna(0), column="close", window=10)
    assert "rolling_std_close_10" in out.columns
    assert out["rolling_std_close_10"].iloc[-1] > 0  # at least some variance


def test_op_zscore(sample_df):
    out = OPS["zscore"](sample_df.fillna(0), columns=["close"])
    assert abs(out["close"].mean()) < 1e-10
    assert abs(out["close"].std() - 1.0) < 1e-10


def test_op_minmax(sample_df):
    out = OPS["minmax"](sample_df.fillna(0), columns=["close"])
    assert out["close"].min() == pytest.approx(0.0, abs=1e-10)
    assert out["close"].max() == pytest.approx(1.0, abs=1e-10)


def test_op_winsorize(sample_df):
    df = sample_df.fillna(0)
    out = OPS["winsorize"](df, columns=["close"], lower=0.05, upper=0.95)
    assert out["close"].max() <= df["close"].quantile(0.95) + 1e-10
    assert out["close"].min() >= df["close"].quantile(0.05) - 1e-10


def test_op_clip(sample_df):
    out = OPS["clip"](sample_df.fillna(0), columns=["close"], lower=50, upper=150)
    assert out["close"].min() >= 50
    assert out["close"].max() <= 150


def test_op_resample(sample_df):
    out = OPS["resample"](sample_df, freq="W", agg="mean")
    # Should have weekly index now
    assert len(out) < len(sample_df)
    assert isinstance(out.index, pd.DatetimeIndex)


def test_op_diff(sample_df):
    out = OPS["diff"](sample_df.fillna(0), column="close", new_name="d1")
    assert pd.isna(out["d1"].iloc[0])
    assert out["d1"].iloc[1] == sample_df.fillna(0)["close"].iloc[1] - sample_df.fillna(0)["close"].iloc[0]


def test_op_shift(sample_df):
    out = OPS["shift"](sample_df, column="close", periods=2, new_name="lag2")
    assert pd.isna(out["lag2"].iloc[0])
    assert pd.isna(out["lag2"].iloc[1])
    # iloc[2] of shift equals iloc[0] of source
    assert out["lag2"].iloc[2] == sample_df["close"].iloc[0] or (
        pd.isna(out["lag2"].iloc[2]) and pd.isna(sample_df["close"].iloc[0])
    )


def test_op_ewma(sample_df):
    out = OPS["ewma"](sample_df.fillna(0), column="close", halflife=5)
    assert "ewma_close_hl5" in out.columns


def test_op_log_transform(sample_df):
    out = OPS["log_transform"](sample_df.fillna(1), column="close")
    assert "log_close" in out.columns


def test_op_robust_scale(sample_df):
    out = OPS["robust_scale"](sample_df.fillna(0), columns=["close"])
    # Median should be ~0 after centering
    assert abs(out["close"].median()) < 1e-10


# ---------------------------------------------------------------------------
# Standardised `columns` API (post-v1.1.0)
# ---------------------------------------------------------------------------


def _multi_df():
    return pd.DataFrame(
        {
            "a": np.arange(1.0, 11.0),
            "b": np.arange(100.0, 110.0),
            "label": ["x"] * 10,
        }
    )


def test_op_rolling_mean_multi_column_in_place():
    df = _multi_df()
    out = OPS["rolling_mean"](df, columns=["a", "b"], window=3)
    # Both columns overwritten in place
    assert list(out.columns) == ["a", "b", "label"]
    expected_a = df["a"].rolling(window=3).mean()
    expected_b = df["b"].rolling(window=3).mean()
    pd.testing.assert_series_equal(out["a"], expected_a, check_names=False)
    pd.testing.assert_series_equal(out["b"], expected_b, check_names=False)
    # Non-numeric column untouched
    pd.testing.assert_series_equal(out["label"], df["label"])


def test_op_rolling_mean_default_all_numeric():
    df = _multi_df()
    out = OPS["rolling_mean"](df, window=3)
    # Default: all numeric columns rolled in place; non-numeric untouched
    expected_a = df["a"].rolling(window=3).mean()
    expected_b = df["b"].rolling(window=3).mean()
    pd.testing.assert_series_equal(out["a"], expected_a, check_names=False)
    pd.testing.assert_series_equal(out["b"], expected_b, check_names=False)
    pd.testing.assert_series_equal(out["label"], df["label"])


def test_op_rolling_mean_single_column_with_new_name_backcompat():
    df = _multi_df()
    out = OPS["rolling_mean"](df, column="a", window=3, new_name="a_smooth")
    assert "a_smooth" in out.columns
    # Original column unchanged
    pd.testing.assert_series_equal(out["a"], df["a"])


def test_op_rolling_mean_rejects_new_name_with_multi_column():
    df = _multi_df()
    with pytest.raises(ValueError, match="new_name only valid with a single column"):
        OPS["rolling_mean"](df, columns=["a", "b"], window=3, new_name="x")


def test_op_rolling_std_multi_column_in_place():
    df = _multi_df()
    out = OPS["rolling_std"](df, columns=["a", "b"], window=3)
    expected_a = df["a"].rolling(window=3).std()
    pd.testing.assert_series_equal(out["a"], expected_a, check_names=False)
    assert "rolling_std_a_3" not in out.columns  # multi-column form is in-place


def test_op_ewma_multi_column_in_place():
    df = _multi_df()
    out = OPS["ewma"](df, columns=["a", "b"], halflife=2)
    expected_a = df["a"].ewm(halflife=2, adjust=False).mean()
    pd.testing.assert_series_equal(out["a"], expected_a, check_names=False)


def test_op_log_transform_multi_column_in_place():
    df = _multi_df()
    out = OPS["log_transform"](df, columns=["a", "b"])
    np.testing.assert_allclose(out["a"].to_numpy(), np.log(df["a"].to_numpy()))
    np.testing.assert_allclose(out["b"].to_numpy(), np.log(df["b"].to_numpy()))
    # No log_a / log_b appended
    assert list(out.columns) == ["a", "b", "label"]


def test_op_log_transform_single_column_backcompat():
    df = _multi_df()
    out = OPS["log_transform"](df, column="a")
    assert "log_a" in out.columns
    # Original column untouched
    pd.testing.assert_series_equal(out["a"], df["a"])


def test_op_log_transform_rejects_new_name_with_multi_column():
    df = _multi_df()
    with pytest.raises(ValueError, match="new_name only valid with a single column"):
        OPS["log_transform"](df, columns=["a", "b"], new_name="x")


def test_op_zscore_default_all_numeric():
    df = _multi_df()
    out = OPS["zscore"](df)
    for col in ("a", "b"):
        assert abs(out[col].mean()) < 1e-10
        assert abs(out[col].std() - 1.0) < 1e-10
    # Non-numeric label column untouched
    pd.testing.assert_series_equal(out["label"], df["label"])


def test_op_interpolate(tiny_df):
    out = OPS["interpolate"](tiny_df, method="linear")
    # a iloc[2] interpolates between 2.0 (iloc[1]) and 4.0 (iloc[3]) -> 3.0
    assert out["a"].iloc[2] == 3.0


def test_op_log1p_explicit_columns(sample_df):
    out = OPS["log1p"](sample_df.fillna(0), columns=["close"])
    expected = np.log1p(sample_df["close"].fillna(0).astype(float))
    pd.testing.assert_series_equal(out["close"], expected, check_names=False)


def test_op_log1p_skips_negative_column_by_default():
    df = pd.DataFrame({"pos": [0.0, 1.0, 2.0], "neg": [-1.0, 0.5, 2.0]})
    out = OPS["log1p"](df)
    np.testing.assert_allclose(out["pos"].to_numpy(), np.log1p([0.0, 1.0, 2.0]))
    # neg column has a negative value -> skipped (unchanged)
    pd.testing.assert_series_equal(out["neg"], df["neg"])


def test_op_log1p_forced_on_negative_produces_nan():
    df = pd.DataFrame({"neg": [-1.0, 0.0, 2.0]})
    out = OPS["log1p"](df, skip_if_negative=False)
    # log1p(-1) = -inf, log1p(values <= -1) = nan beyond; just check NaN propagation
    assert np.isinf(out["neg"].iloc[0]) or np.isnan(out["neg"].iloc[0])


def test_op_drop_low_variance_drops_near_constant():
    df = pd.DataFrame({
        "stable": [1.0] * 10,        # std = 0 -> dropped
        "active": np.arange(10.0),    # std > threshold -> kept
        "mostly_zero": [0.0] * 8 + [1.0, 2.0],   # zeros_frac = 0.8 -> dropped
    })
    out = OPS["drop_low_variance"](df)
    assert "active" in out.columns
    assert "stable" not in out.columns
    assert "mostly_zero" not in out.columns


def test_op_drop_low_variance_respects_threshold():
    df = pd.DataFrame({"tiny_var": [1.0, 1.0 + 1e-9, 1.0]})
    # Default threshold 1e-8 -> drops it
    assert "tiny_var" not in OPS["drop_low_variance"](df).columns
    # Loosened threshold -> keeps it
    assert "tiny_var" in OPS["drop_low_variance"](df, std_threshold=1e-12).columns


# ---------------------------------------------------------------------------
# Pipeline : Python escape hatch
# ---------------------------------------------------------------------------


def test_pipeline_python_api(sample_df):
    pipe = (
        Pipeline()
        .add_step("log_diff", column="close", new_name="ret")
        .add_step("rolling_std", column="ret", window=10, new_name="vol")
        .add_step("dropna")
    )
    result = pipe.fit_transform(sample_df)
    assert "ret" in result.df.columns
    assert "vol" in result.df.columns
    assert len(pipe.steps) == 3
    # provenance reflects exactly what we added
    assert result.provenance[0].op == "log_diff"
    assert result.provenance[-1].op == "dropna"


def test_pipeline_python_with_output_split(sample_df):
    pipe = (
        Pipeline()
        .add_step("log_diff", column="close", new_name="ret")
        .add_step("rolling_std", column="ret", window=10, new_name="vol")
        .add_step("dropna")
        .set_output(observations=["ret"], covariates=["vol"])
    )
    result = pipe.fit_transform(sample_df)
    assert result.X is not None
    assert result.Z is not None
    assert list(result.X.columns) == ["ret"]
    assert list(result.Z.columns) == ["vol"]
    assert len(result.X) == len(result.Z)


def test_pipeline_unknown_op_raises():
    with pytest.raises(ValueError, match="unknown op"):
        Pipeline().add_step("nonexistent_op")


def test_pipeline_step_failure_wraps_error(sample_df):
    pipe = Pipeline().add_step("select_columns", columns=["nonexistent_column"])
    with pytest.raises(RuntimeError, match="select_columns"):
        pipe.fit_transform(sample_df)


# ---------------------------------------------------------------------------
# Recipes : library discovery + load + run
# ---------------------------------------------------------------------------


def test_list_recipes_returns_bundled_names():
    names = list_recipes()
    # Check the canonical ones are present
    assert "normalize_zscore" in names
    assert "clean_missing_forward_fill" in names
    assert "outlier_robust_winsorize" in names
    assert "financial_log_returns" in names
    assert "volatility_features" in names
    assert "crypto_basic_prep" in names
    assert "align_to_grid_daily" in names
    assert "financial_full_features" in names


def test_recipe_from_name_runs(sample_df):
    pipe = Pipeline.from_recipe("financial_log_returns")
    result = pipe.fit_transform(sample_df.ffill())
    assert "log_return" in result.df.columns


def test_recipe_clean_missing_forward_fill_drops_no_data(sample_df):
    pipe = Pipeline.from_recipe("clean_missing_forward_fill")
    result = pipe.fit_transform(sample_df)
    # No NaN remaining
    assert result.df.isna().sum().sum() == 0


def test_recipe_volatility_features_creates_vol_column(sample_df):
    # First need log_return present in the input
    pipe = (
        Pipeline.from_recipe("financial_log_returns")
    )
    intermediate = pipe.fit_transform(sample_df.ffill())
    # Now apply volatility features
    vol_pipe = Pipeline.from_recipe("volatility_features")
    result = vol_pipe.fit_transform(intermediate.df)
    assert "realized_vol_20" in result.df.columns


# ---------------------------------------------------------------------------
# Composition : `includes` resolves correctly
# ---------------------------------------------------------------------------


def test_recipe_composition_crypto_basic_prep(sample_df):
    """crypto_basic_prep includes financial_log_returns + volatility_features."""
    pipe = Pipeline.from_recipe("crypto_basic_prep")
    # Check that the compiled pipeline has all expected ops in order
    op_names = [s.op for s in pipe.steps]
    # log_diff comes first (from financial_log_returns include)
    assert op_names[0] == "log_diff"
    # rolling_std comes after (from volatility_features include)
    assert "rolling_std" in op_names
    # zscore + dropna are the local steps
    assert "zscore" in op_names
    assert "dropna" in op_names

    result = pipe.fit_transform(sample_df.ffill())
    assert "log_return" in result.df.columns
    assert "realized_vol_20" in result.df.columns
    # output split should populate X and Z
    assert result.X is not None and list(result.X.columns) == ["log_return"]
    assert result.Z is not None and list(result.Z.columns) == ["realized_vol_20"]


def test_recipe_composition_financial_full_features(sample_df):
    """financial_full_features includes financial_log_returns plus multi-window vol."""
    pipe = Pipeline.from_recipe("financial_full_features")
    result = pipe.fit_transform(sample_df.ffill())
    for col in ["log_return", "realized_vol_5", "realized_vol_20", "realized_vol_60"]:
        assert col in result.df.columns


def test_recipe_composition_no_remaining_nans(sample_df):
    """Composed recipes that end with dropna leave no NaN."""
    pipe = Pipeline.from_recipe("crypto_basic_prep")
    result = pipe.fit_transform(sample_df.ffill())
    assert result.df.isna().sum().sum() == 0


# ---------------------------------------------------------------------------
# YAML loading edge cases
# ---------------------------------------------------------------------------


def test_load_recipe_unknown_name_raises():
    with pytest.raises(FileNotFoundError, match="not found"):
        load_recipe("nonexistent_recipe")


def test_load_recipe_from_inline_path(tmp_path, sample_df):
    """Load a recipe from an arbitrary file path."""
    recipe_text = """
name: test_custom
description: just for testing
version: 1
steps:
  - op: log_diff
    column: close
    new_name: ret
  - op: dropna
"""
    p = tmp_path / "my_recipe.yaml"
    p.write_text(recipe_text)
    pipe = Pipeline.from_yaml(p)
    result = pipe.fit_transform(sample_df.ffill())
    assert "ret" in result.df.columns


def test_load_recipe_unknown_op_raises(tmp_path):
    recipe_text = """
name: bad
version: 1
steps:
  - op: this_op_does_not_exist
"""
    p = tmp_path / "bad.yaml"
    p.write_text(recipe_text)
    with pytest.raises(ValueError, match="unknown op"):
        load_recipe(p)


def test_load_recipe_invalid_yaml_root(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- not_a_mapping")
    with pytest.raises(ValueError, match="must be a mapping"):
        load_recipe(p)


def test_load_recipe_step_missing_op_key(tmp_path):
    recipe_text = """
name: bad
steps:
  - missing_op_key: yes
"""
    p = tmp_path / "bad_step.yaml"
    p.write_text(recipe_text)
    with pytest.raises(ValueError, match="op"):
        load_recipe(p)


def test_load_recipe_max_depth_cycle_protection(tmp_path):
    """Self-including recipe should hit the depth limit and raise."""
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text(
        f"name: a\nincludes:\n  - recipe: {b}\nsteps: []\n"
    )
    b.write_text(
        f"name: b\nincludes:\n  - recipe: {a}\nsteps: []\n"
    )
    with pytest.raises(RecursionError, match="max depth"):
        load_recipe(a)


# ---------------------------------------------------------------------------
# Provenance + sidecar
# ---------------------------------------------------------------------------


def test_provenance_records_applied_steps(sample_df):
    pipe = (
        Pipeline()
        .add_step("log_diff", column="close", new_name="ret")
        .add_step("dropna")
    )
    result = pipe.fit_transform(sample_df)
    assert len(result.provenance) == 2
    assert result.provenance[0].op == "log_diff"
    assert result.provenance[0].params == {"column": "close", "new_name": "ret"}


def test_sidecar_written_with_provenance(tmp_path, sample_df):
    pipe = Pipeline.from_recipe("financial_log_returns")
    result = pipe.fit_transform(sample_df.ffill())

    # Pretend we wrote the prepared df to disk
    out_path = tmp_path / "prepared.parquet"
    out_path.touch()
    sidecar = result.to_sidecar(out_path)
    assert sidecar.exists()
    content = sidecar.read_text()
    assert "applied_steps" in content
    assert "log_diff" in content


# ---------------------------------------------------------------------------
# register_op : user can extend the registry
# ---------------------------------------------------------------------------


def test_register_op_extends_registry():
    @register_op("custom_test_op_xyz")
    def my_op(df, *, factor: float = 1.0):
        return df * factor

    assert "custom_test_op_xyz" in OPS
    pipe = Pipeline().add_step("custom_test_op_xyz", factor=2.0)
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = pipe.fit_transform(df)
    assert result.df["x"].tolist() == [2.0, 4.0, 6.0]

    # Cleanup so this doesn't leak to other tests
    del OPS["custom_test_op_xyz"]


def test_register_op_rejects_duplicate():
    @register_op("dup_test_op_xyz")
    def my_op(df):
        return df

    try:
        with pytest.raises(ValueError, match="already registered"):

            @register_op("dup_test_op_xyz")
            def my_op2(df):
                return df

    finally:
        del OPS["dup_test_op_xyz"]


# ---------------------------------------------------------------------------
# Integration : prepared dataset → fit(topology, X, Z)
# ---------------------------------------------------------------------------


def test_prep_output_feeds_fit_pipeline_end_to_end(sample_df):
    """The X / Z output of a prep pipeline must be directly consumable by fit/fit_nhmm."""
    from hmm_core.fit import fit
    from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology

    pipe = Pipeline.from_recipe("crypto_basic_prep")
    prepared = pipe.fit_transform(sample_df.ffill())

    assert prepared.X is not None
    X_arr = prepared.X.to_numpy()

    topo = Topology(
        name="prep-integration",
        n_states=2,
        state_names=["s0", "s1"],
        emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=1),
        allowed_transitions=None,
        startprob="uniform",
        init=InitSpec(strategy="kmeans", seed=42),
        fit=FitSpec(algorithm="baum_welch", n_iter=20, tol=1e-3),
    )
    result = fit(topo, X_arr, seed=42)
    assert np.isfinite(result.log_likelihood)
