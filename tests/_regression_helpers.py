"""Shared helpers for fit-regression tests.

Pattern :
    1. Load a CSV via a recipe + apply optional post-prep transforms (e.g. PCA).
    2. Load a Topology YAML and run ``fit()`` on the prepared X.
    3. Compare ``fitted.to_summary_dict()`` against a reference dict within
       per-field tolerance.

Used by ``tests/test_valentin_eth_regression.py`` and any future
regression test that pins a published reference fit. Keeps each
regression file thin — most of them are just data path + tolerances +
reference numbers.

See ``FittedModel.to_summary_dict()`` for the canonical set of fields a
reference dict can contain.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest

# Default per-field tolerances. Override by passing ``tol`` to
# ``assert_summary_matches_reference``.
DEFAULT_REL_TOL = 0.05  # 5% relative tolerance on numeric fields
DEFAULT_ABS_TOL_BIC = 0.0  # use relative
DEFAULT_ITER_RANGE_FACTOR = 5  # actual must be in [ref/5, ref*5]


def env_csv_path(env_var: str) -> Path | None:
    """Return ``Path`` from ``$env_var`` if set and the file exists, else None.

    Convention for private datasets : test modules call
    ``pytestmark = pytest.mark.skipif(env_csv_path(VAR) is None, reason=...)``.
    """
    raw = os.environ.get(env_var)
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def skipif_env_missing(env_var: str, dataset_name: str) -> Any:
    """Build a pytest skipif marker for a private-dataset env var.

    Use at module level :
        pytestmark = skipif_env_missing("HMM_VALENTIN_ETH_PATH", "Valentin ETH")
    """
    return pytest.mark.skipif(
        env_csv_path(env_var) is None,
        reason=(
            f"{env_var} is unset or does not point at an existing file. "
            f"Set it to the absolute path of the {dataset_name} dataset to "
            f"run this regression."
        ),
    )


@dataclass(frozen=True)
class RegressionReference:
    """Reference values + tolerances for a single regression test.

    Use as the canonical pin point for what a healthy fit should look
    like. ``summary`` must be a subset of ``FittedModel.to_summary_dict()``
    keys (extra fields are allowed in the actual fit; we only check the
    ones you pin).

    Tolerances :
        - numeric fields default to ``rel_tol`` (relative).
        - ``n_iter_actual`` uses ``iter_range`` if set, else
          ``[ref/iter_range_factor, ref*iter_range_factor]``.
        - boolean / string fields must match exactly.
        - per-field overrides via ``per_field_tol = {"log_likelihood": 0.01}``.
    """

    summary: dict[str, Any]
    rel_tol: float = DEFAULT_REL_TOL
    iter_range: tuple[int, int] | None = None
    iter_range_factor: int = DEFAULT_ITER_RANGE_FACTOR
    per_field_tol: dict[str, float] = field(default_factory=dict)


def assert_summary_matches_reference(
    actual: dict[str, Any],
    reference: RegressionReference,
) -> None:
    """Compare ``actual`` (from ``fitted.to_summary_dict()``) to ``reference``.

    Fails on the first mismatch with a clear message indicating field,
    expected, actual, tolerance.
    """
    ref = reference.summary
    for key, ref_val in ref.items():
        if key not in actual:
            raise AssertionError(
                f"reference key {key!r} missing from actual summary " f"(keys: {sorted(actual)})"
            )
        act_val = actual[key]

        # Special-case n_iter_actual
        if key == "n_iter_actual":
            lo, hi = reference.iter_range or (
                max(1, int(ref_val) // reference.iter_range_factor),
                int(ref_val) * reference.iter_range_factor,
            )
            assert lo <= int(act_val) <= hi, (
                f"{key}: got {act_val}, expected within [{lo}, {hi}] " f"(reference {ref_val})"
            )
            continue

        # Exact match for booleans and strings
        if isinstance(ref_val, bool) or isinstance(ref_val, str):
            assert (
                act_val == ref_val
            ), f"{key}: got {act_val!r}, expected exact match to {ref_val!r}"
            continue

        # None expected -> actual must be None too
        if ref_val is None:
            assert act_val is None, f"{key}: got {act_val!r}, expected None"
            continue

        # Numeric : relative tolerance (per-field override or default)
        tol = reference.per_field_tol.get(key, reference.rel_tol)
        ref_abs = abs(float(ref_val))
        if ref_abs == 0:
            # ref is exactly 0 -> require actual within absolute tol
            assert abs(float(act_val)) <= tol, f"{key}: got {act_val}, expected ~0 (abs tol {tol})"
        else:
            rel_err = abs(float(act_val) - float(ref_val)) / ref_abs
            assert rel_err < tol, (
                f"{key}: got {act_val:.6g}, reference {ref_val:.6g} "
                f"(relative error {rel_err:.3%}, tol {tol:.0%})"
            )


def run_recipe_fit(
    csv_path: Path,
    recipe_name: str,
    topology_yaml: Path,
    *,
    csv_kwargs: dict[str, Any] | None = None,
    sort_index_col: str | None = None,
    post_prep: Callable[[Any], Any] | None = None,
    fit_seed: int = 42,
) -> dict[str, Any]:
    """Load CSV → recipe → optional post-prep transform → fit → summary dict.

    Returns the dict ``fitted.to_summary_dict()`` (plus a few extras for
    diagnostics: ``prep_rows`` and ``post_prep_shape``). The caller's
    regression test compares this against a ``RegressionReference``.

    Parameters
    ----------
    csv_path
        Absolute path to the input CSV.
    recipe_name
        Bundled recipe name (e.g. ``"valentin_eth"``).
    topology_yaml
        Absolute path to a Topology YAML file.
    csv_kwargs
        Forwarded to ``pd.read_csv`` (e.g. ``encoding="ISO-8859-1"``).
    sort_index_col
        If provided, sort by this column and set it as the index after read.
    post_prep
        Optional ``df -> X`` transform applied after the recipe's
        ``fit_transform`` returns. Typical use: PCA reduction.
        Default: pass the prepared DataFrame's values through.
    fit_seed
        Forwarded to ``fit()``.
    """
    import warnings

    import pandas as pd

    from hmm_core.fit import fit
    from hmm_core.io import load_topology
    from hmm_core.prep import Pipeline

    csv_kwargs = csv_kwargs or {}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        df = pd.read_csv(csv_path, **csv_kwargs)
        if sort_index_col is not None:
            df = df.sort_values(sort_index_col).set_index(sort_index_col)

        prep = Pipeline.from_recipe(recipe_name).fit_transform(df)
        prep_rows = prep.df.shape[0]

        X = post_prep(prep.df) if post_prep is not None else prep.df.values
        post_prep_shape = tuple(getattr(X, "shape", (len(X),)))

        topo = load_topology(str(topology_yaml))
        fitted = fit(topo, X, seed=fit_seed)

    summary = fitted.to_summary_dict()
    summary["prep_rows"] = prep_rows
    summary["post_prep_shape"] = post_prep_shape
    return summary
