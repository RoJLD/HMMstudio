"""Recipe parser and Pipeline executor for the data prep layer (B.11).

A ``Recipe`` is a declarative YAML description of a sequence of pandas
transformations. The engine :
    1. Parses the YAML
    2. Resolves recursive ``includes`` (composition of recipes)
    3. Compiles to a flat list of ``(op_name, params)`` steps
    4. Executes via the ``Pipeline`` class

A ``Pipeline`` is also constructible directly in Python (escape hatch) for
cases where YAML is too constraining.

After ``fit_transform``, a ``PreparedResult`` is returned containing the
transformed DataFrame, optionally split into ``X`` (observations) and ``Z``
(covariates), and the **provenance trace** (the exact list of steps
applied with resolved parameters).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from hmm_core.prep.ops import OPS

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecipeStep:
    """One atomic step in a compiled pipeline."""

    op: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.op, **self.params}


@dataclass(frozen=True)
class OutputSpec:
    """Optional observation / covariate split on the final DataFrame."""

    observations: list[str] = field(default_factory=list)
    covariates: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Recipe:
    """Compiled recipe : a flat sequence of steps, ready for execution."""

    name: str
    description: str
    version: int
    steps: list[RecipeStep]
    output: OutputSpec | None = None
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.output:
            out["output"] = {
                "observations": list(self.output.observations),
                "covariates": list(self.output.covariates),
            }
        return out


@dataclass(frozen=True)
class PreparedResult:
    """Output of ``Pipeline.fit_transform``.

    Attributes
    ----------
    df
        The fully prepared DataFrame.
    X
        Observation array (shape (T, n_obs_features)) if output.observations
        was set ; otherwise None.
    Z
        Covariate array (shape (T, n_cov_features)) if output.covariates was
        set ; otherwise None.
    provenance
        List of ``RecipeStep`` actually applied (after composition resolution
        and parameter overrides). Suitable for writing a sidecar yaml.
    """

    df: pd.DataFrame
    X: pd.DataFrame | None
    Z: pd.DataFrame | None
    provenance: list[RecipeStep]

    def to_sidecar(self, output_path: Path) -> Path:
        """Write a sidecar yaml describing the applied recipe."""
        sidecar = output_path.parent / f"{output_path.name}.recipe.yaml"
        sidecar.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "applied_steps": [s.to_dict() for s in self.provenance],
                },
                sort_keys=False,
            )
        )
        return sidecar

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter (Phase I.1)."""
        from hmm_core._jupyter import render_chip_list, render_stats_table, wrap_html

        T, n_cols = self.df.shape
        n_nan = int(self.df.isna().sum().sum())

        stats_rows = [
            ("Output shape", f"{T} rows × {n_cols} cols"),
            ("Remaining NaN", f"{n_nan}"),
            ("Applied steps", len(self.provenance)),
            ("Columns", render_chip_list(list(self.df.columns)[:10])),
        ]
        if self.X is not None:
            stats_rows.append(
                ("Observations (X)", f"shape {self.X.shape}, columns: {list(self.X.columns)}")
            )
        if self.Z is not None:
            stats_rows.append(
                ("Covariates (Z)", f"shape {self.Z.shape}, columns: {list(self.Z.columns)}")
            )
        stats_html = render_stats_table(stats_rows)

        # Preview first 5 rows via pandas's _repr_html_
        try:
            preview_html = "<h5>First 5 rows</h5>" + self.df.head(5).to_html(
                max_cols=8, classes="dataframe"
            )
        except Exception:
            preview_html = ""

        return wrap_html(
            "<h4>PreparedResult</h4>",
            stats_html,
            preview_html,
        )


# ---------------------------------------------------------------------------
# Recipe lookup
# ---------------------------------------------------------------------------


def _bundled_recipes_dir() -> Path:
    return Path(__file__).parent / "recipes"


def list_recipes() -> list[str]:
    """Names of all bundled canonical recipes."""
    return sorted(p.stem for p in _bundled_recipes_dir().glob("*.yaml"))


def _resolve_recipe_path(name_or_path: str | Path) -> Path:
    """If ``name_or_path`` is a file, return it. Else look it up in bundled recipes."""
    p = Path(name_or_path)
    if p.exists():
        return p
    bundled = _bundled_recipes_dir() / f"{name_or_path}.yaml"
    if bundled.exists():
        return bundled
    raise FileNotFoundError(
        f"recipe {name_or_path!r} not found ; "
        f"tried path={p} and bundled={bundled}. "
        f"Available bundled recipes : {list_recipes()}"
    )


# ---------------------------------------------------------------------------
# Recipe loader (with recursive composition)
# ---------------------------------------------------------------------------


def load_recipe(
    name_or_path: str | Path,
    *,
    _depth: int = 0,
    _max_depth: int = 8,
) -> Recipe:
    """Load and compile a recipe by name or path. Resolves ``includes`` recursively.

    Composition semantics :
        - ``includes: [{recipe: foo, params: {...}}, ...]`` is processed in order
          BEFORE the recipe's own ``steps``.
        - Each include is itself a recipe (resolved recursively up to
          ``_max_depth`` to prevent cycles).
        - ``params`` in an include do NOT override the included recipe's step
          parameters individually — they're forwarded as the include's
          OWN params (for now we only support **no parameter substitution**
          inside included recipes ; if you need parametrization, write the
          recipe with explicit Python construction instead). This keeps
          composition simple and predictable.
    """
    if _depth > _max_depth:
        raise RecursionError(
            f"recipe composition exceeded max depth {_max_depth} "
            f"(possible cycle in `includes` ?)"
        )

    path = _resolve_recipe_path(name_or_path)
    spec = yaml.safe_load(path.read_text())

    if not isinstance(spec, dict):
        raise ValueError(f"recipe {path} : YAML root must be a mapping")

    name = spec.get("name") or path.stem
    description = spec.get("description", "")
    version = int(spec.get("version", 1))

    compiled_steps: list[RecipeStep] = []

    # 1. Resolve includes
    for include_spec in spec.get("includes", []) or []:
        if isinstance(include_spec, str):
            include_spec = {"recipe": include_spec, "params": {}}
        if not isinstance(include_spec, dict) or "recipe" not in include_spec:
            raise ValueError(f"include must be a mapping with 'recipe' key, got {include_spec!r}")
        sub_recipe = load_recipe(include_spec["recipe"], _depth=_depth + 1, _max_depth=_max_depth)
        # Optional parameter overrides for the included recipe
        override = include_spec.get("params", {}) or {}
        for sub_step in sub_recipe.steps:
            merged_params = {**sub_step.params, **override}
            compiled_steps.append(RecipeStep(op=sub_step.op, params=merged_params))

    # 2. Append local steps
    for raw_step in spec.get("steps", []) or []:
        if not isinstance(raw_step, dict) or "op" not in raw_step:
            raise ValueError(f"step must be a mapping with 'op' key, got {raw_step!r}")
        op_name = raw_step["op"]
        params = {k: v for k, v in raw_step.items() if k != "op"}
        compiled_steps.append(RecipeStep(op=op_name, params=params))

    # 3. Parse output spec
    output = None
    if "output" in spec:
        raw_out = spec["output"]
        if isinstance(raw_out, dict):
            output = OutputSpec(
                observations=list(raw_out.get("observations", [])),
                covariates=list(raw_out.get("covariates", [])),
            )

    # 4. Validate all op names refer to registered ops (only at top level —
    #    we don't validate within sub-recipes again since they were validated
    #    during their own load).
    if _depth == 0:
        for step in compiled_steps:
            if step.op not in OPS:
                raise ValueError(f"unknown op : {step.op!r}. " f"Registered ops : {sorted(OPS)}")

    return Recipe(
        name=name,
        description=description,
        version=version,
        steps=compiled_steps,
        output=output,
        source_path=path,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class Pipeline:
    """Sequence of ops applied to a DataFrame.

    Three ways to construct :
        - ``Pipeline.from_yaml(path)`` — load a YAML file
        - ``Pipeline.from_recipe(name)`` — load a bundled recipe by name
        - ``Pipeline()`` + ``.add_step(op, **params)`` — Python escape hatch
    """

    def __init__(self) -> None:
        self._steps: list[RecipeStep] = []
        self._output: OutputSpec | None = None
        self._recipe_name: str = "anonymous"
        self._recipe_description: str = ""

    # --- constructors ---

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Pipeline":
        recipe = load_recipe(path)
        return cls._from_recipe(recipe)

    @classmethod
    def from_recipe(cls, name: str) -> "Pipeline":
        recipe = load_recipe(name)
        return cls._from_recipe(recipe)

    @classmethod
    def _from_recipe(cls, recipe: Recipe) -> "Pipeline":
        pipe = cls()
        pipe._steps = list(recipe.steps)
        pipe._output = recipe.output
        pipe._recipe_name = recipe.name
        pipe._recipe_description = recipe.description
        return pipe

    # --- builder ---

    def add_step(self, op: str, **params: Any) -> "Pipeline":
        """Append a step. Returns self for chaining."""
        if op not in OPS:
            raise ValueError(f"unknown op : {op!r}. Registered ops : {sorted(OPS)}")
        self._steps.append(RecipeStep(op=op, params=params))
        return self

    def set_output(
        self,
        observations: list[str] | None = None,
        covariates: list[str] | None = None,
    ) -> "Pipeline":
        self._output = OutputSpec(
            observations=observations or [],
            covariates=covariates or [],
        )
        return self

    # --- inspection ---

    @property
    def steps(self) -> list[RecipeStep]:
        return list(self._steps)

    @property
    def name(self) -> str:
        return self._recipe_name

    # --- execution ---

    def fit_transform(self, df: pd.DataFrame) -> PreparedResult:
        """Apply all steps in order, return a PreparedResult."""
        current = df.copy()
        for step in self._steps:
            op_fn = OPS[step.op]
            try:
                current = op_fn(current, **step.params)
            except Exception as e:
                raise RuntimeError(
                    f"prep step {step.op!r} with params {step.params} failed : {e}"
                ) from e

        X = None
        Z = None
        if self._output is not None:
            if self._output.observations:
                missing = set(self._output.observations) - set(current.columns)
                if missing:
                    raise ValueError(f"observations columns not in prepared df : {missing}")
                X = current[list(self._output.observations)]
            if self._output.covariates:
                missing = set(self._output.covariates) - set(current.columns)
                if missing:
                    raise ValueError(f"covariates columns not in prepared df : {missing}")
                Z = current[list(self._output.covariates)]

        return PreparedResult(
            df=current,
            X=X,
            Z=Z,
            provenance=list(self._steps),
        )

    def __repr__(self) -> str:
        return (
            f"Pipeline(name={self._recipe_name!r}, "
            f"n_steps={len(self._steps)}, "
            f"output={self._output})"
        )

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter (Phase I.1)."""
        from hmm_core._jupyter import render_chip_list, render_stats_table, wrap_html, _esc

        # Steps table
        steps_rows = ["<h5>Pipeline steps</h5>"]
        steps_rows.append("<table><tr><th>#</th><th>Op</th><th>Parameters</th></tr>")
        for i, step in enumerate(self._steps):
            params_str = ", ".join(f"{k}={v!r}" for k, v in step.params.items())
            steps_rows.append(
                f"<tr><td>{i + 1}</td><td><code>{_esc(step.op)}</code></td>"
                f"<td style='text-align:left'><code>{_esc(params_str)}</code></td></tr>"
            )
        steps_rows.append("</table>")

        stats_rows = [("Name", self._recipe_name), ("Steps", len(self._steps))]
        if self._output is not None:
            stats_rows.append(("Observations", render_chip_list(self._output.observations)))
            stats_rows.append(("Covariates", render_chip_list(self._output.covariates)))
        stats_html = render_stats_table(stats_rows)

        if self._recipe_description:
            desc_html = (
                f'<div class="small" style="margin: 4px 0">{_esc(self._recipe_description)}</div>'
            )
        else:
            desc_html = ""

        return wrap_html(
            "<h4>Pipeline</h4>",
            stats_html,
            desc_html,
            "".join(steps_rows),
        )
