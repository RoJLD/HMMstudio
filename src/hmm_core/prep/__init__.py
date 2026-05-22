"""Data preparation layer (Phase B.11).

Composable recipe-driven preprocessing pipelines for tabular data. Designed
to bridge raw datasets (from the warehouse, Phase B.10) and HMM-ready
observations/covariates.

Architecture :
    - **Ops** (atomic transformations) : ~20 pandas-thin functions :
      normalization, forward-fill, log-diff, rolling features, resampling.
      The engine itself is **general-purpose preprocessing**, not
      HMM-specific.
    - **Engine** : YAML recipe parser + Pipeline executor with recursive
      ``includes`` composition + sidecar provenance.
    - **Library** : 8 bundled canonical recipes shipped in
      ``hmm_core.prep.recipes`` — 4 general (normalize, forward-fill,
      winsorize, resample) + 4 HMM-canonical (log returns, volatility
      features, crypto basic prep, train-ready split).

Three usage modes :

1. **YAML recipe by path** ::

    from hmm_core.prep import Pipeline
    pipe = Pipeline.from_yaml("recipe.yaml")
    prepared = pipe.fit_transform(raw_df)

2. **Builtin recipe by name** ::

    pipe = Pipeline.from_recipe("crypto_basic_prep")
    prepared = pipe.fit_transform(raw_df)

3. **Python escape hatch** ::

    pipe = Pipeline()
    pipe.add_step("log_diff", column="close", new_name="log_return")
    pipe.add_step("rolling_std", column="log_return", window=20)
    pipe.add_step("zscore", columns=["log_return", "rolling_std_20"])
    prepared = pipe.fit_transform(raw_df)

Anti-scope-creep guardrails (see docs/decisions/0011-prep-layer-scope.md) :

- NO custom DSL — recipes are declarative YAML over pandas
- NO scheduling / batch — interactive use only
- NO multi-dataset joins — out of scope
- NO model fitting in recipes — they're transforms only
"""

from __future__ import annotations

from hmm_core.prep.engine import (
    Pipeline,
    PreparedResult,
    Recipe,
    list_recipes,
    load_recipe,
)
from hmm_core.prep.ops import OPS, register_op

__all__ = [
    "OPS",
    "Pipeline",
    "PreparedResult",
    "Recipe",
    "list_recipes",
    "load_recipe",
    "register_op",
]
