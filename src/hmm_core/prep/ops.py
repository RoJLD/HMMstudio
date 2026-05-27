"""Atomic operations for the data prep engine.

Each op is a callable ``(df: pd.DataFrame, **params) -> pd.DataFrame``. Ops
are pure (no side effects beyond returning a new DataFrame). They live in
the ``OPS`` registry, keyed by name.

Categories :
    - Column manipulation : select_columns, drop_columns, rename_columns
    - Missing data        : fillna_forward, fillna_backward, fillna_value,
                            interpolate, dropna
    - Transformations     : log_diff, diff, pct_change, log_transform, shift
    - Rolling features    : rolling_mean, rolling_std, ewma
    - Scaling             : zscore, minmax, robust_scale
    - Outlier handling    : winsorize, clip
    - Time / resampling   : resample

Adding a new op : decorate with ``@register_op("name")`` (signature must be
``(df, **params) -> df``).
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

OPS: dict[str, Callable[..., pd.DataFrame]] = {}


def register_op(name: str) -> Callable[[Callable], Callable]:
    """Decorator : register a function as an op in OPS."""

    def decorator(fn: Callable) -> Callable:
        if name in OPS:
            raise ValueError(f"op {name!r} already registered")
        OPS[name] = fn
        return fn

    return decorator


def _resolve_columns(
    df: pd.DataFrame,
    columns: list[str] | None,
    column: str | None,
) -> list[str]:
    """Resolve target columns for per-column ops.

    Resolution order :
        - ``column="x"`` (legacy single-column form) -> ``["x"]``
        - ``columns=["x", "y"]`` -> ``["x", "y"]``
        - both None -> every numeric column of ``df``.
    """
    if column is not None and columns is not None:
        raise ValueError("pass either `column` (single) or `columns` (list), not both")
    if column is not None:
        return [column]
    if columns is not None:
        return list(columns)
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


# ---------------------------------------------------------------------------
# Column manipulation
# ---------------------------------------------------------------------------


@register_op("select_columns")
def select_columns(df: pd.DataFrame, *, columns: list[str]) -> pd.DataFrame:
    return df[list(columns)].copy()


@register_op("drop_columns")
def drop_columns(df: pd.DataFrame, *, columns: list[str]) -> pd.DataFrame:
    return df.drop(columns=list(columns))


@register_op("rename_columns")
def rename_columns(df: pd.DataFrame, *, mapping: dict[str, str]) -> pd.DataFrame:
    return df.rename(columns=mapping)


# ---------------------------------------------------------------------------
# Missing data
# ---------------------------------------------------------------------------


@register_op("fillna_forward")
def fillna_forward(
    df: pd.DataFrame, *, columns: list[str] | None = None, limit: int | None = None
) -> pd.DataFrame:
    out = df.copy()
    cols = columns if columns is not None else out.columns.tolist()
    out[cols] = out[cols].ffill(limit=limit)
    return out


@register_op("fillna_backward")
def fillna_backward(
    df: pd.DataFrame, *, columns: list[str] | None = None, limit: int | None = None
) -> pd.DataFrame:
    out = df.copy()
    cols = columns if columns is not None else out.columns.tolist()
    out[cols] = out[cols].bfill(limit=limit)
    return out


@register_op("fillna_value")
def fillna_value(
    df: pd.DataFrame, *, value: float, columns: list[str] | None = None
) -> pd.DataFrame:
    out = df.copy()
    if columns is None:
        return out.fillna(value)
    out[columns] = out[columns].fillna(value)
    return out


@register_op("interpolate")
def interpolate(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    method: str = "linear",
    limit: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    cols = columns if columns is not None else out.columns.tolist()
    out[cols] = out[cols].interpolate(method=method, limit=limit)
    return out


@register_op("dropna")
def dropna(df: pd.DataFrame, *, columns: list[str] | None = None) -> pd.DataFrame:
    if columns is None:
        return df.dropna()
    return df.dropna(subset=list(columns))


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------


@register_op("log_diff")
def log_diff(df: pd.DataFrame, *, column: str, new_name: str | None = None) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"{column}_logdiff"
    out[name] = np.log(out[column].astype(float)).diff()
    return out


@register_op("diff")
def diff(
    df: pd.DataFrame,
    *,
    column: str,
    periods: int = 1,
    new_name: str | None = None,
) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"{column}_diff{periods}"
    out[name] = out[column].diff(periods=periods)
    return out


@register_op("pct_change")
def pct_change(
    df: pd.DataFrame,
    *,
    column: str,
    periods: int = 1,
    new_name: str | None = None,
) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"{column}_pctchange{periods}"
    out[name] = out[column].pct_change(periods=periods)
    return out


@register_op("log_transform")
def log_transform(
    df: pd.DataFrame,
    *,
    column: str | None = None,
    columns: list[str] | None = None,
    new_name: str | None = None,
) -> pd.DataFrame:
    """Replace listed columns by ``log(col)``.

    - Single-column form: ``column="x"`` (legacy) writes to ``new_name`` if
      provided, else to ``log_{column}``.
    - Multi-column form: ``columns=["a", "b"]`` overwrites each in place.
      Defaults to every numeric column when both args are omitted.
    - ``new_name`` is only valid with the single-column form.
    """
    targets = _resolve_columns(df, columns, column)
    is_single_legacy = column is not None
    if new_name is not None and not is_single_legacy:
        raise ValueError("new_name only valid with a single column")

    out = df.copy()
    if is_single_legacy:
        name = new_name or f"log_{column}"
        out[name] = np.log(out[column].astype(float))
        return out
    for col in targets:
        out[col] = np.log(out[col].astype(float))
    return out


@register_op("select_features_unsupervised")
def select_features_unsupervised(
    df: pd.DataFrame,
    *,
    n_clusters: int = 10,
    n_neighbors: int = 5,
    linkage_method: str = "average",
    jitter_std: float = 1e-8,
    random_state: int = 42,
) -> pd.DataFrame:
    """Keep one medoid feature per NMI-cluster (unsupervised selection).

    Thin recipe-friendly wrapper around
    :func:`hmm_core.features.unsupervised_feature_selection` : clusters the
    candidate columns by normalised mutual information and returns only the
    selected (decorrelated) subset of columns — a ``df -> df`` op.

    The rich metadata (NMI matrix, clusters) is not exposed in the pipeline ;
    call ``unsupervised_feature_selection`` directly to inspect it. NaN rows
    must be dropped upstream (e.g. a preceding ``dropna`` step) — the k-NN MI
    estimator needs clean input.
    """
    # Imported lazily: pulls sklearn/scipy, which we keep out of the
    # module-load path for the prep package.
    from hmm_core.features import unsupervised_feature_selection

    return unsupervised_feature_selection(
        df,
        n_clusters=n_clusters,
        n_neighbors=n_neighbors,
        linkage_method=linkage_method,
        jitter_std=jitter_std,
        random_state=random_state,
    ).selected


@register_op("drop_low_variance")
def drop_low_variance(
    df: pd.DataFrame,
    *,
    std_threshold: float = 1e-8,
    zeros_fraction_max: float = 0.5,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Drop columns that are degenerate for downstream modeling.

    Two filters apply (a column is dropped if EITHER triggers):
    - ``std(col) < std_threshold`` — near-constant column.
    - ``mean(col == 0) > zeros_fraction_max`` — sparse / mostly-zero column.

    ``columns`` restricts the check to a subset (default: every numeric
    column). Non-numeric columns are never touched.
    """
    out = df.copy()
    candidates = (
        columns
        if columns is not None
        else [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]
    )
    to_drop: list[str] = []
    for col in candidates:
        col_vals = out[col].astype(float)
        if col_vals.std() < std_threshold:
            to_drop.append(col)
            continue
        if (col_vals == 0).mean() > zeros_fraction_max:
            to_drop.append(col)
    return out.drop(columns=to_drop)


@register_op("log1p")
def log1p(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    skip_if_negative: bool = True,
) -> pd.DataFrame:
    """Replace each listed column by ``log1p(col)`` in place.

    If ``columns`` is None, applies to every numeric column. By default skips
    columns that contain any negative value (``skip_if_negative=True``) so
    the op is safe to chain after a generic preprocessing step. Pass
    ``skip_if_negative=False`` to force log1p (which will produce NaN on
    negatives, matching ``numpy.log1p`` behavior).
    """
    out = df.copy()
    target = (
        columns
        if columns is not None
        else [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]
    )
    for col in target:
        col_vals = out[col].astype(float)
        if skip_if_negative and (col_vals < 0).any():
            continue
        out[col] = np.log1p(col_vals)
    return out


@register_op("shift")
def shift(
    df: pd.DataFrame,
    *,
    column: str,
    periods: int = 1,
    new_name: str | None = None,
) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"{column}_shift{periods}"
    out[name] = out[column].shift(periods=periods)
    return out


# ---------------------------------------------------------------------------
# Rolling features
# ---------------------------------------------------------------------------


@register_op("rolling_mean")
def rolling_mean(
    df: pd.DataFrame,
    *,
    window: int,
    column: str | None = None,
    columns: list[str] | None = None,
    new_name: str | None = None,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Rolling mean per column.

    - Single-column form (legacy): ``column="x"`` produces a new column
      named ``new_name`` if given, else ``rolling_mean_{column}_{window}``.
    - Multi-column form: ``columns=["a", "b"]`` overwrites each column in
      place. Defaults to all numeric columns when both args are omitted.
    - ``new_name`` is only valid with the single-column form.
    """
    targets = _resolve_columns(df, columns, column)
    is_single_legacy = column is not None
    if new_name is not None and not is_single_legacy:
        raise ValueError("new_name only valid with a single column")

    out = df.copy()
    if is_single_legacy:
        name = new_name or f"rolling_mean_{column}_{window}"
        out[name] = out[column].rolling(window=window, min_periods=min_periods).mean()
        return out
    for col in targets:
        out[col] = out[col].rolling(window=window, min_periods=min_periods).mean()
    return out


@register_op("rolling_std")
def rolling_std(
    df: pd.DataFrame,
    *,
    window: int,
    column: str | None = None,
    columns: list[str] | None = None,
    new_name: str | None = None,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Rolling standard deviation per column. See ``rolling_mean`` for the
    column-selection contract and backwards-compatibility rules."""
    targets = _resolve_columns(df, columns, column)
    is_single_legacy = column is not None
    if new_name is not None and not is_single_legacy:
        raise ValueError("new_name only valid with a single column")

    out = df.copy()
    if is_single_legacy:
        name = new_name or f"rolling_std_{column}_{window}"
        out[name] = out[column].rolling(window=window, min_periods=min_periods).std()
        return out
    for col in targets:
        out[col] = out[col].rolling(window=window, min_periods=min_periods).std()
    return out


@register_op("ewma")
def ewma(
    df: pd.DataFrame,
    *,
    column: str | None = None,
    columns: list[str] | None = None,
    halflife: float | None = None,
    span: float | None = None,
    new_name: str | None = None,
) -> pd.DataFrame:
    """Exponentially weighted moving average per column. See ``rolling_mean``
    for the column-selection contract and backwards-compatibility rules."""
    if halflife is None and span is None:
        raise ValueError("ewma requires one of halflife or span")
    targets = _resolve_columns(df, columns, column)
    is_single_legacy = column is not None
    if new_name is not None and not is_single_legacy:
        raise ValueError("new_name only valid with a single column")

    out = df.copy()
    if is_single_legacy:
        suffix = f"hl{halflife}" if halflife is not None else f"span{span}"
        name = new_name or f"ewma_{column}_{suffix}"
        out[name] = out[column].ewm(halflife=halflife, span=span, adjust=False).mean()
        return out
    for col in targets:
        out[col] = out[col].ewm(halflife=halflife, span=span, adjust=False).mean()
    return out


# ---------------------------------------------------------------------------
# Scaling
# ---------------------------------------------------------------------------


@register_op("zscore")
def zscore(df: pd.DataFrame, *, columns: list[str] | None = None) -> pd.DataFrame:
    """Standardise each column to mean 0 / std 1. Defaults to all numeric columns."""
    targets = _resolve_columns(df, columns, None)
    out = df.copy()
    for col in targets:
        mu = out[col].mean()
        sigma = out[col].std()
        if sigma == 0 or pd.isna(sigma):
            out[col] = out[col] - mu
        else:
            out[col] = (out[col] - mu) / sigma
    return out


@register_op("minmax")
def minmax(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    feature_range: tuple[float, float] = (0.0, 1.0),
) -> pd.DataFrame:
    """Rescale to ``feature_range``. Defaults to all numeric columns."""
    targets = _resolve_columns(df, columns, None)
    lo, hi = feature_range
    out = df.copy()
    for col in targets:
        col_min = out[col].min()
        col_max = out[col].max()
        spread = col_max - col_min
        if spread == 0 or pd.isna(spread):
            out[col] = lo
        else:
            out[col] = lo + (out[col] - col_min) * (hi - lo) / spread
    return out


@register_op("robust_scale")
def robust_scale(df: pd.DataFrame, *, columns: list[str] | None = None) -> pd.DataFrame:
    """Median + IQR scaling — robust to outliers. Defaults to all numeric columns."""
    targets = _resolve_columns(df, columns, None)
    out = df.copy()
    for col in targets:
        median = out[col].median()
        q1 = out[col].quantile(0.25)
        q3 = out[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            out[col] = out[col] - median
        else:
            out[col] = (out[col] - median) / iqr
    return out


# ---------------------------------------------------------------------------
# Outlier handling
# ---------------------------------------------------------------------------


@register_op("winsorize")
def winsorize(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    lower: float = 0.01,
    upper: float = 0.99,
) -> pd.DataFrame:
    """Clip each column to quantile bounds. Defaults to all numeric columns."""
    targets = _resolve_columns(df, columns, None)
    out = df.copy()
    for col in targets:
        lo = out[col].quantile(lower)
        hi = out[col].quantile(upper)
        out[col] = out[col].clip(lower=lo, upper=hi)
    return out


@register_op("clip")
def clip(
    df: pd.DataFrame,
    *,
    columns: list[str],
    lower: float | None = None,
    upper: float | None = None,
) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        out[col] = out[col].clip(lower=lower, upper=upper)
    return out


# ---------------------------------------------------------------------------
# Resampling (time series)
# ---------------------------------------------------------------------------


@register_op("resample")
def resample(
    df: pd.DataFrame,
    *,
    freq: str,
    agg: str = "mean",
    index_col: str | None = None,
) -> pd.DataFrame:
    """Resample to a new frequency (pandas offset alias : 'D', 'H', '15min', ...).

    If ``index_col`` is given, sets it as the DatetimeIndex first. Otherwise
    expects df.index to already be a DatetimeIndex.
    """
    src = df.copy()
    if index_col is not None:
        src = src.set_index(index_col)
        src.index = pd.to_datetime(src.index)
    if not isinstance(src.index, pd.DatetimeIndex):
        raise ValueError(
            "resample requires a DatetimeIndex ; "
            "pass `index_col=...` or set df.index to a DatetimeIndex first"
        )
    resampler = src.resample(freq)
    if agg == "mean":
        out = resampler.mean()
    elif agg == "sum":
        out = resampler.sum()
    elif agg == "last":
        out = resampler.last()
    elif agg == "first":
        out = resampler.first()
    elif agg == "ohlc":
        out = resampler.ohlc()
    else:
        raise ValueError(f"unsupported resample agg : {agg!r}")
    return out
