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
def log_diff(
    df: pd.DataFrame, *, column: str, new_name: str | None = None
) -> pd.DataFrame:
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
    df: pd.DataFrame, *, column: str, new_name: str | None = None
) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"log_{column}"
    out[name] = np.log(out[column].astype(float))
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
    column: str,
    window: int,
    new_name: str | None = None,
    min_periods: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"rolling_mean_{column}_{window}"
    out[name] = out[column].rolling(window=window, min_periods=min_periods).mean()
    return out


@register_op("rolling_std")
def rolling_std(
    df: pd.DataFrame,
    *,
    column: str,
    window: int,
    new_name: str | None = None,
    min_periods: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    name = new_name or f"rolling_std_{column}_{window}"
    out[name] = out[column].rolling(window=window, min_periods=min_periods).std()
    return out


@register_op("ewma")
def ewma(
    df: pd.DataFrame,
    *,
    column: str,
    halflife: float | None = None,
    span: float | None = None,
    new_name: str | None = None,
) -> pd.DataFrame:
    if halflife is None and span is None:
        raise ValueError("ewma requires one of halflife or span")
    out = df.copy()
    suffix = f"hl{halflife}" if halflife is not None else f"span{span}"
    name = new_name or f"ewma_{column}_{suffix}"
    out[name] = (
        out[column]
        .ewm(halflife=halflife, span=span, adjust=False)
        .mean()
    )
    return out


# ---------------------------------------------------------------------------
# Scaling
# ---------------------------------------------------------------------------


@register_op("zscore")
def zscore(df: pd.DataFrame, *, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        mu = out[col].mean()
        sigma = out[col].std()
        if sigma == 0 or pd.isna(sigma):
            out[col] = out[col] - mu
        else:
            out[col] = (out[col] - mu) / sigma
    return out


@register_op("minmax")
def minmax(
    df: pd.DataFrame, *, columns: list[str], feature_range: tuple[float, float] = (0.0, 1.0)
) -> pd.DataFrame:
    lo, hi = feature_range
    out = df.copy()
    for col in columns:
        col_min = out[col].min()
        col_max = out[col].max()
        spread = col_max - col_min
        if spread == 0 or pd.isna(spread):
            out[col] = lo
        else:
            out[col] = lo + (out[col] - col_min) * (hi - lo) / spread
    return out


@register_op("robust_scale")
def robust_scale(df: pd.DataFrame, *, columns: list[str]) -> pd.DataFrame:
    """Median + IQR scaling — robust to outliers."""
    out = df.copy()
    for col in columns:
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
    columns: list[str],
    lower: float = 0.01,
    upper: float = 0.99,
) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
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
