# Model-selection Phase 2 — CLI `hmm-fit compare` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `hmm-fit compare` subcommand that fits several candidate topologies on the same data and prints a ranked BIC/AIC/HQIC table.

**Architecture:** Thin CLI layer over the already-shipped `hmm_core.selection.compare_models` / `auto_grid` (Phase 1). The command loads candidate topologies either from a directory of `*.yaml` files (one comparable `TopologyCandidate` each) or from an optional `grid.yaml` describing an `auto_grid`, reads one data CSV as a float matrix, calls `compare_models`, and prints a ranked plain-text table in the same style as the existing `hmm-fit batch`. NHMM/Factorial are deliberately out of scope for the CLI (they need explicit covariates/chain specs).

**Tech Stack:** Python, Typer (CLI), pandas (CSV), PyYAML (grid.yaml), pytest + `typer.testing.CliRunner`.

**Spec:** `docs/specs/2026-05-27-model-variant-selection.md` (Phase 2 section + open question #1 = grid.yaml schema, resolved here).

**Prerequisites (shipped):** Phase 1 core — `compare_models`, `auto_grid`, `TopologyCandidate`, `ModelComparison` (with `.ranked(criterion)`, `best_by_bic/aic/hqic`) exported at `hmm_core` top level (`112af47`).

---

## Design notes (read before starting)

- **Output style:** match `hmm-fit batch` — plain `typer.echo` formatted columns, **no Rich table** (the spec says "Rich table" loosely, but `batch`, the cited precedent, uses plain echo, and the spec also mandates "aucune nouvelle dépendance"). `rich` is NOT a declared dependency.
- **Ranking:** reuse `ModelComparison.ranked(criterion)` — it already returns comparable candidates sorted ascending by the criterion, then errored/non-comparable rows in insertion order. Mark non-comparable / errored rows with `⚠`, the best row with `★`.
- **Data reading:** read the CSV once as a float matrix (`df.to_numpy(dtype=float)`) and hand the single `X` to `compare_models`. Comparable candidates (Gaussian/GMM/Poisson) all consume the same `(n, n_features)` matrix. A candidate whose `n_features` mismatches (or a stray multinomial) fails inside `compare_models`, which captures it as an errored row — non-fatal, as designed in Phase 1.
- **grid.yaml schema** (resolves open question #1):
  ```yaml
  base: base.yaml          # path to a base topology YAML, relative to spec_dir
  k_range: [2, 3, 4]       # explicit list of K values
  emission_types: [gaussian, gmm]   # optional, default [gaussian]
  n_mix: 2                 # optional, default 2 (used only for gmm candidates)
  ```
  When `spec_dir/grid.yaml` exists it takes precedence and the directory's other `*.yaml` files are ignored (the `base` is loaded via its `base:` reference, not as a standalone candidate).
- **Exit codes:** exit 0 iff at least one comparable candidate converged (i.e. `best_by_<criterion>` is not `None`). Empty/missing spec_dir or no candidates → exit 1 with a clear message. A non-converging set (every comparable candidate errored) → exit 1.

## File Structure

- Modify: `src/hmm_core/cli.py` — add the `compare` command + three module-level helpers (`_candidates_from_dir`, `_candidates_from_grid`, `_print_comparison`).
- Modify: `tests/test_cli.py` — add 6 tests for the new command.
- Modify: `CHANGELOG.md` — note the new CLI command under `[Unreleased]`.

---

### Task 1: `hmm-fit compare` ranks a directory of topology candidates

**Files:**
- Modify: `src/hmm_core/cli.py` (add `compare` command + `_candidates_from_dir` + `_print_comparison` helpers, after the `batch` block, before `if __name__ == "__main__":`)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_compare_cli_ranks_dir -v`
Expected: FAIL — `compare` is not a registered command (typer exits with code 2 / "No such command").

- [ ] **Step 3: Write the command + helpers**

In `src/hmm_core/cli.py`, add after the `_print_progress_line` function (and before `if __name__ == "__main__":`):

```python
def _candidates_from_dir(spec_dir: Path, pattern: str) -> list:
    """Load every matching *.yaml in spec_dir as a comparable TopologyCandidate.

    A `grid.yaml` (if any) is skipped here — it is handled by the grid path.
    """
    from hmm_core.selection import TopologyCandidate

    out: list = []
    for ypath in sorted(spec_dir.glob(pattern)):
        if ypath.name == "grid.yaml":
            continue
        topo = load_topology(ypath)
        out.append(TopologyCandidate(topology=topo))
    return out


def _print_comparison(comp, criterion: str) -> None:
    """Print a ranked, fixed-width comparison table (batch-style plain echo)."""
    best = getattr(comp, f"best_by_{criterion}")

    def fmt(v: float) -> str:
        return f"{'-':>12s}" if v != v else f"{v:>12.2f}"  # v != v catches NaN

    typer.echo(f"Model comparison (ranked by {criterion.upper()}) - best: {best or '-'}")
    typer.echo(
        f"  {'candidate':30s} {'kind':10s} "
        f"{'log_lik':>12s} {'BIC':>12s} {'AIC':>12s} {'HQIC':>12s}  note"
    )
    for c in comp.ranked(criterion):
        ok = c.comparable and c.error is None
        star = " *" if c.label == best else ""
        mark = "" if ok else " !"
        note = c.error or c.note or ""
        label = f"{c.label}{star}{mark}"
        typer.echo(
            f"  {label:30s} {c.kind:10s} "
            f"{fmt(c.log_likelihood)} {fmt(c.bic)} {fmt(c.aic)} {fmt(c.hqic)}  {note}"
        )


@app.command()
def compare(
    spec_dir: Path,
    data_path: Path,
    criterion: str = typer.Option(
        "bic", "--criterion", "-c", help="Ranking criterion: bic | aic | hqic"
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", help="Override init seed for all candidate fits"
    ),
    pattern: str = typer.Option("*.yaml", help="Glob for candidate topology files in spec_dir"),
) -> None:
    """Fit several candidate topologies on the SAME data and rank them by criterion.

    spec_dir holds one *.yaml topology per comparable candidate (Gaussian / GMM /
    Poisson - they model P(X)). Alternatively, a `grid.yaml` in spec_dir describes
    an auto-generated emission x K grid (keys: base, k_range, emission_types, n_mix).

    NHMM / Factorial candidates are NOT available via the CLI - they need explicit
    covariates / chain specs. Use the Python API (hmm_core.compare_models) for those.
    """
    from hmm_core.selection import compare_models

    if criterion not in ("bic", "aic", "hqic"):
        raise typer.BadParameter("criterion must be one of: bic, aic, hqic")

    spec_dir = spec_dir.resolve()
    if not spec_dir.exists() or not spec_dir.is_dir():
        typer.echo(f"spec_dir does not exist or is not a directory: {spec_dir}", err=True)
        raise typer.Exit(code=1)

    grid_path = spec_dir / "grid.yaml"
    if grid_path.exists():
        candidates = _candidates_from_grid(grid_path, spec_dir)
    else:
        candidates = _candidates_from_dir(spec_dir, pattern)

    if not candidates:
        typer.echo(
            f"no candidate topologies found in {spec_dir} (pattern {pattern!r})", err=True
        )
        raise typer.Exit(code=1)

    df = pd.read_csv(data_path)
    X = df.to_numpy(dtype=float)

    comp = compare_models(X, candidates, seed=(seed if seed is not None else 42))
    _print_comparison(comp, criterion)

    if getattr(comp, f"best_by_{criterion}") is None:
        typer.echo("no comparable candidate converged", err=True)
        raise typer.Exit(code=1)
```

Note: `_candidates_from_grid` is defined in Task 3. To keep this task self-contained and runnable, also add a temporary stub now and replace it in Task 3:

```python
def _candidates_from_grid(grid_path: Path, spec_dir: Path) -> list:
    raise typer.BadParameter("grid.yaml support is added in Task 3")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_compare_cli_ranks_dir -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hmm_core/cli.py tests/test_cli.py
git commit -F .git/COMMIT_MSG_TEMP.txt
```
(Write the message to `.git/COMMIT_MSG_TEMP.txt` first — here-strings break on embedded quotes.)
Message: `feat(cli): hmm-fit compare ranks a directory of topology candidates`

---

### Task 2: empty / missing spec_dir exits non-zero with a clear message

**Files:**
- Test: `tests/test_cli.py`
- (No production change — Task 1 already added the guards; this task locks the behavior with a test.)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it passes immediately**

Run: `python -m pytest tests/test_cli.py::test_compare_cli_no_candidates_exits_nonzero -v`
Expected: PASS (the guard added in Task 1 emits "no candidate topologies found" and exits 1). If it FAILS, the guard text/exit code regressed — fix the guard in `compare`, do not weaken the test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -F .git/COMMIT_MSG_TEMP.txt
```
Message: `test(cli): compare exits non-zero on empty candidate dir`

---

### Task 3: grid.yaml drives an auto-generated emission x K grid

**Files:**
- Modify: `src/hmm_core/cli.py` (replace the `_candidates_from_grid` stub from Task 1 with the real implementation)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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

    result = runner.invoke(
        app, ["compare", str(spec_dir), str(data_csv), "--criterion", "hqic"]
    )
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    assert "hqic" in out
    assert "k=2" in out and "k=3" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_compare_cli_grid_yaml -v`
Expected: FAIL — the Task 1 stub raises `BadParameter("grid.yaml support is added in Task 3")` → non-zero exit.

- [ ] **Step 3: Replace the stub with the real implementation**

In `src/hmm_core/cli.py`, replace the `_candidates_from_grid` stub with:

```python
def _candidates_from_grid(grid_path: Path, spec_dir: Path) -> list:
    """Build an emission x K grid of TopologyCandidates from a grid.yaml.

    grid.yaml keys: base (path to a base topology YAML, relative to spec_dir),
    k_range (list of ints), emission_types (list, default ["gaussian"]),
    n_mix (int, default 2 - used only for gmm candidates).
    """
    import yaml

    from hmm_core.selection import auto_grid

    spec = yaml.safe_load(grid_path.read_text(encoding="utf-8")) or {}
    base_ref = spec.get("base")
    if not base_ref:
        raise typer.BadParameter("grid.yaml must have a 'base' key (path to a base topology YAML)")
    base_topo = load_topology(spec_dir / base_ref)

    k_range = spec.get("k_range")
    if not k_range:
        raise typer.BadParameter("grid.yaml must have a non-empty 'k_range' list")

    emission_types = spec.get("emission_types") or ["gaussian"]
    n_mix = int(spec.get("n_mix", 2))
    return auto_grid(base_topo, list(k_range), emission_types, n_mix=n_mix)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_compare_cli_grid_yaml -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hmm_core/cli.py tests/test_cli.py
git commit -F .git/COMMIT_MSG_TEMP.txt
```
Message: `feat(cli): grid.yaml expands a base topology into an emission x K grid`

---

### Task 4: --help surfaces the command and the NHMM/Factorial limitation

**Files:**
- Test: `tests/test_cli.py`
- (No production change — the docstring written in Task 1 carries the note; this task locks it.)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass immediately**

Run: `python -m pytest tests/test_cli.py -k "compare_in_app_help or compare_help_notes" -v`
Expected: PASS (the Task 1 docstring contains "NHMM / Factorial ... Use the Python API"). If `test_compare_help_notes_nhmm_limitation` FAILS, the docstring lost the note — restore it.

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -F .git/COMMIT_MSG_TEMP.txt
```
Message: `test(cli): compare appears in help and documents the NHMM/Factorial limit`

---

### Task 5: full suite green + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run the compare tests as a group**

Run: `python -m pytest tests/test_cli.py -k compare -v`
Expected: 6 passed (ranks_dir, no_candidates, grid_yaml, in_app_help, help_notes_nhmm, and they coexist).

- [ ] **Step 2: Run the full CLI test module**

Run: `python -m pytest tests/test_cli.py -q`
Expected: all pass (existing batch/run/decode/show tests + 6 new compare tests).

- [ ] **Step 3: Update CHANGELOG**

In `CHANGELOG.md`, under the `[Unreleased]` → `### Added` section, add a bullet:

```markdown
- `hmm-fit compare <spec_dir> <data.csv> [--criterion bic|aic|hqic]` — fit several
  candidate topologies on the same data and print a ranked BIC/AIC/HQIC table.
  Candidates come from a directory of topology YAMLs or an optional `grid.yaml`
  (`base`, `k_range`, `emission_types`, `n_mix`). NHMM/Factorial remain Python-API only.
```

(If no `[Unreleased]` section exists, add one above the latest version heading. Match the existing CHANGELOG heading style.)

- [ ] **Step 4: Optional — CLI reference doc**

Run: `git grep -l "hmm-fit batch" docs/` (or Grep `hmm-fit batch` in `docs/`).
If a CLI reference page lists `batch`, add a `compare` subsection mirroring its format. If no such page exists, skip — do not invent one.

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md
# plus any docs file touched in Step 4
git commit -F .git/COMMIT_MSG_TEMP.txt
```
Message: `docs(cli): changelog for hmm-fit compare`

---

## Definition of done (Phase 2, per spec §6)

- [ ] `hmm-fit compare` command in `hmm_core/cli.py` (dir + grid.yaml sources, `--criterion`, ranked table, exit codes).
- [ ] 6 CLI tests green (spec required 2: ranks_dir + no_candidates; +4 added: grid, in-app help, help-note, group run).
- [ ] Full `tests/test_cli.py` green.
- [ ] CHANGELOG `[Unreleased]` updated.
- [ ] Open question #1 (grid.yaml schema) resolved: `base` / `k_range` / `emission_types` / `n_mix`.

## Out of scope (deferred to Phase 3 / future)

- Web UI `/compare` page + `POST /api/compare/start` — Phase 3 (its own plan).
- NHMM / Factorial via CLI — needs Z/chains, not expressible in flat YAML dir (spec §3 Phase 2).
- Multinomial candidates in a compare dir — the CSV is read as a float matrix; a multinomial candidate would error and show as a non-fatal `⚠` row. Not a supported path.

## Self-review (run before handing off)

- **Spec coverage:** Phase 2 section (`hmm-fit compare`, `--criterion`, dir + grid.yaml, ranked table, exit-0-iff-comparable-converged, --help NHMM note) → Tasks 1-5. Both spec-required tests present (Task 1, Task 2). ✓
- **Placeholder scan:** every code step shows full code; the only deliberate stub (`_candidates_from_grid` in Task 1) is explicitly replaced in Task 3. ✓
- **Type consistency:** helper names `_candidates_from_dir` / `_candidates_from_grid` / `_print_comparison` and the `compare` signature are identical across Tasks 1 and 3. Uses real Phase-1 API: `compare_models(X, candidates, seed=...)`, `ModelComparison.ranked(criterion)`, `best_by_<criterion>`, `auto_grid(base, k_range, emission_types, n_mix=...)`, `TopologyCandidate(topology=...)` — all verified against `src/hmm_core/selection.py`. ✓
