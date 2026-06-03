# dcor as alternative criterion for unsupervised_feature_selection — Implementation Plan

> ## Status — paused 2026-05-28
>
> **Branch :** `academy-emission-lessons` (hmm_studio). Sub-project B (lessons 14+15) is
> staged on the same branch — the user will split the commits at their end.
>
> **Venv :** `C:\Users\rdenis\VScode\Tools\hmm_studio\.venv` (Python 3.12.1). hmm_studio
> is installed editable. `dcor` IS installed (verified : `.venv/Lib/site-packages/dcor/`
> exists). All tests must be run with this venv's Python, e.g.
> `"$VENV/Scripts/python.exe" -m pytest tests/test_features.py -q`.
>
> **Done :**
> - **Task 1** — `[dcor]` extra appended to `pyproject.toml` (staged) ; `dcor>=0.6`
>   installed in `.venv`. Verified : `grep -n "^dcor" pyproject.toml` returns the new
>   line. No baseline lint/test run was logged in this session (machine was
>   contention-heavy), so the resumer should re-run the Task 1 Step 1 baseline
>   `pytest tests/test_features.py -q` before starting Task 2 — to confirm a green
>   pre-change state.
>
> **Pending :** Tasks 2 → 9 untouched. The seven files this plan modifies are
> currently in their original state, except `pyproject.toml` (Task 1 edit, staged).
>
> **How to resume :**
> 1. `cd C:\Users\rdenis\VScode\Tools\hmm_studio`.
> 2. Verify branch : `git branch --show-current` → `academy-emission-lessons`.
> 3. Verify venv : `"$PWD/.venv/Scripts/python.exe" -c "import hmm_core, dcor; print('OK', dcor.__version__)"`.
> 4. Baseline : `"$PWD/.venv/Scripts/python.exe" -m pytest tests/test_features.py -q`.
>    Must pass on the pre-change codebase.
> 5. Resume at Task 2 (refactor `_cluster_and_pick_medoids` helper). The plan's
>    Task 2 → 9 are complete and self-contained — sub-agent-driven or inline
>    execution work identically.
>
> **Crypto-repo state (sub-project A) :** 26 files staged on branch
> `benchmark-rebenchmark` of `Experiment.Crypto.2026S1.NathanBerbinau` (benchmark
> package + tests + results + spec/plan + README rewrite). Not yet committed.
>
> **hmm_studio staged set as of pause :** `pyproject.toml` (C/T1),
> `docs/sources/academy-references.md` (B), `src/hmm_studio/frontend/src/lessons/index.ts`
> (B), `src/hmm_studio/frontend/src/lessons/lesson-14-comparing-models.tsx` (B),
> `src/hmm_studio/frontend/src/lessons/lesson-15-choosing-emission.tsx` (B). Untracked
> but ready : `docs/superpowers/` (both B and C specs/plans). The user's pre-existing
> modifications (`AGENTS.md`, `CLAUDE.md`, `roadmap.yml`) are unrelated to this work.
>

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `criterion: str = "nmi"` parameter to `hmm_core.features.unsupervised_feature_selection()` that accepts `"nmi"` (default, current behaviour) or `"dcor"` (distance correlation via the optional `dcor` extra), keeping the existing API and tests fully backward-compatible while teaching the trade-off in Academy lesson 13.

**Architecture:** Pure backend change in `hmm_core` (a private helper extraction + a new similarity-matrix builder + a lazy-imported dcor branch + a field rename with a backward-compat property alias) plus a wrapper passthrough in the prep op, plus a frontend lesson update and a bibliography update. No new component, no new module file — the change lives inside `features.py`, `prep/ops.py`, `pyproject.toml`, `tests/test_features.py`, one Academy lesson, the central bibliography, and a dated update to the existing 2026-05-27 spec.

**Tech Stack:** Python 3.12, numpy/pandas, scikit-learn (existing), `dcor>=0.6` (new optional extra), scipy. Frontend: React/TS/Vite/Tailwind (touch only one TSX lesson). Tests via pytest.

**Spec:** `docs/superpowers/specs/2026-05-28-features-dcor-criterion-design.md`

**Execution convention:** Python commands from the repo root `C:\Users\rdenis\VScode\Tools\hmm_studio\`. Frontend (`npm run lint && npm run build`) from `src/hmm_studio/frontend/`.

**Branch policy:** Continue on the existing feature branch `academy-emission-lessons` (B is staged but not committed there — the user decided to split commits at their end). If the branch was renamed, verify before starting: `git branch --show-current`.

**Commit policy:** the user handles commits. At each task's end, stage with `git add` and STOP. Do NOT run `git commit`. The commit lines below describe the intended commit for reference only.

---

## Task 1: Setup — declare `[dcor]` extra + install for dev

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Confirm clean baseline**

Run (from repo root): `pytest tests/test_features.py -q`
Expected: all existing feature tests pass (the file has 192 lines of tests; the count should match the pre-change baseline). If anything fails, STOP and escalate — this plan assumes a green baseline.

- [ ] **Step 2: Add the `[dcor]` extra to `pyproject.toml`**

Locate the `[project.optional-dependencies]` block. After the `web` extra entry and before the `dev` extra entry (or wherever a stable alphabetical-ish slot fits the file's order — currently `web` then `dev`), insert a new extra:

```toml
dcor = ["dcor>=0.6"]
```

Concretely the patch is one insertion. Find this block:

```toml
[project.optional-dependencies]
web = [
    "fastapi>=0.115",
    ...
]
dev = [
    "pytest>=8.0",
    ...
]
```

Insert between the closing `]` of `web = [...]` and the opening `dev = [`:

```toml
dcor = ["dcor>=0.6"]
```

- [ ] **Step 3: Install the extra in the current Python environment**

Run (from repo root): `pip install -e ".[dcor]"`
Expected: `Successfully installed dcor-X.Y.Z` (or "Requirement already satisfied" if dcor is already present).

Verify the import works: `python -c "import dcor; print('dcor', dcor.__version__); print(dcor.distance_correlation([1.0,2,3,4],[1.0,2,3,4]))"`
Expected: prints a version number and `1.0` (perfect correlation of a series with itself).

- [ ] **Step 4: Re-run the existing tests with the extra installed**

Run: `pytest tests/test_features.py -q`
Expected: same green result as Step 1 (the extra changes nothing for the NMI path).

- [ ] **Step 5: Stage (no commit)**

Run: `git add pyproject.toml`

Intended commit (left to user): `feat(features): declare optional [dcor] extra`

---

## Task 2: Extract `_cluster_and_pick_medoids` helper (pure refactor, no behaviour change)

**Files:**
- Modify: `src/hmm_core/features.py`

This is a pure refactor — same tests, same outputs. The goal is to isolate the "similarity → distance → linkage → fcluster → medoids" pipeline so Task 4 can plug a different similarity matrix into it.

- [ ] **Step 1: Add the helper above `unsupervised_feature_selection`**

In `src/hmm_core/features.py`, insert this new private function immediately before the existing `def unsupervised_feature_selection(` line:

```python
def _cluster_and_pick_medoids(
    similarity_matrix: np.ndarray,
    columns: list[str],
    n_clusters: int,
    linkage_method: str,
) -> tuple[dict[int, str], dict[int, list[str]], list[str]]:
    """Cluster + medoid pipeline shared by every criterion.

    Parameters
    ----------
    similarity_matrix
        Symmetric ``(p, p)`` matrix with values in ``[0, 1]`` and ``1.0`` on the
        diagonal (higher = more redundant).
    columns
        Feature names, length ``p``, in the same order as the matrix.
    n_clusters
        Number of clusters to cut the dendrogram at.
    linkage_method
        scipy.cluster.hierarchy linkage method (``"average"`` is the documented
        default for NMI-style 1-similarity distances).

    Returns
    -------
    medoid_per_cluster : dict[int, str]
    cluster_dict       : dict[int, list[str]]
    selected_names     : list[str]  (one medoid per cluster, sorted by cluster id)
    """
    distance = 1.0 - similarity_matrix
    np.fill_diagonal(distance, 0.0)
    distance = 0.5 * (distance + distance.T)
    linkage = hierarchy.linkage(
        squareform(distance, checks=False), method=linkage_method
    )
    cluster_ids = hierarchy.fcluster(linkage, n_clusters, criterion="maxclust")

    clusters: dict[int, list[str]] = defaultdict(list)
    for name, cid in zip(columns, cluster_ids, strict=False):
        clusters[int(cid)].append(name)

    medoids: dict[int, str] = {}
    selected_names: list[str] = []
    for cid, cols in sorted(clusters.items()):
        if len(cols) == 1:
            medoid = cols[0]
        else:
            idxs = [columns.index(c) for c in cols]
            sub = similarity_matrix[np.ix_(idxs, idxs)].copy()
            np.fill_diagonal(sub, 0.0)
            centrality = sub.mean(axis=1)
            medoid = cols[int(np.argmax(centrality))]
        medoids[cid] = medoid
        selected_names.append(medoid)

    return medoids, dict(clusters), selected_names
```

- [ ] **Step 2: Rewire `unsupervised_feature_selection` to call the helper**

In the SAME file, locate the existing body of `unsupervised_feature_selection` from `distance = 1.0 - nmi_matrix` down to the `return FeatureSelectionResult(...)` line. Replace that whole tail block (everything after the line `np.fill_diagonal(nmi_matrix, 1.0)`) with:

```python
    medoids, clusters, selected_names = _cluster_and_pick_medoids(
        similarity_matrix=nmi_matrix,
        columns=columns,
        n_clusters=n_clusters,
        linkage_method=linkage_method,
    )

    return FeatureSelectionResult(
        selected=features[selected_names],
        nmi_matrix=nmi_matrix,
        cluster_dict=clusters,
        medoid_per_cluster=medoids,
    )
```

(The intermediate steps that built `distance`, ran `linkage`, ran `fcluster`, and computed medoids are now ALL inside `_cluster_and_pick_medoids`. They must be removed from the outer function so the logic is not duplicated.)

- [ ] **Step 3: Verify the refactor preserved behaviour**

Run: `pytest tests/test_features.py -q`
Expected: same green pass count as before the refactor — every existing test stays green (this is a pure-refactor task; if anything fails, the helper or its call site has a bug).

- [ ] **Step 4: Stage (no commit)**

Run: `git add src/hmm_core/features.py`

Intended commit (left to user): `refactor(features): extract _cluster_and_pick_medoids helper`

---

## Task 3: Rename `nmi_matrix` field → `similarity_matrix` with a backward-compat property alias

**Files:**
- Modify: `src/hmm_core/features.py`
- Test (new): `tests/test_features.py` (append one test for the alias)

- [ ] **Step 1: Add the failing alias test**

In `tests/test_features.py`, append at the very end of the file:

```python
def test_similarity_matrix_alias_equivalence(independent_df):
    """`result.similarity_matrix` and `result.nmi_matrix` must point at the same
    array — `nmi_matrix` is a backward-compat alias."""
    result = unsupervised_feature_selection(independent_df, n_clusters=3)
    assert hasattr(result, "similarity_matrix")
    assert result.similarity_matrix is result.nmi_matrix
```

- [ ] **Step 2: Run the new test, verify it FAILS**

Run: `pytest tests/test_features.py::test_similarity_matrix_alias_equivalence -v`
Expected: FAIL with `AttributeError: 'FeatureSelectionResult' object has no attribute 'similarity_matrix'`.

- [ ] **Step 3: Rename the dataclass field and add the alias property**

In `src/hmm_core/features.py`, locate the `FeatureSelectionResult` dataclass. Replace its body (the four field declarations) with:

```python
@dataclass(frozen=True)
class FeatureSelectionResult:
    """Rich output of :func:`unsupervised_feature_selection`.

    Attributes
    ----------
    selected
        ``features[medoids]`` — the selected subset, input row index preserved.
        One column per cluster.
    similarity_matrix
        The full ``(p, p)`` matrix of feature-pair similarity in ``[0, 1]``,
        symmetric with ``1.0`` on the diagonal. Contains NMI when the selector
        ran with ``criterion="nmi"`` (the default), or dcor values when
        ``criterion="dcor"``. Useful for a diagnostic heatmap.
    cluster_dict
        Mapping ``cluster_id -> list of feature names`` in that cluster.
    medoid_per_cluster
        Mapping ``cluster_id -> medoid feature name`` (the retained column).
    """

    selected: pd.DataFrame
    similarity_matrix: np.ndarray
    cluster_dict: dict[int, list[str]]
    medoid_per_cluster: dict[int, str]

    @property
    def nmi_matrix(self) -> np.ndarray:
        """Legacy alias for :attr:`similarity_matrix` (kept for backward compat)."""
        return self.similarity_matrix
```

- [ ] **Step 4: Update the constructor call in `unsupervised_feature_selection`**

In the same file, locate the final `return FeatureSelectionResult(...)` line at the bottom of `unsupervised_feature_selection`. Replace the keyword `nmi_matrix=nmi_matrix,` with `similarity_matrix=nmi_matrix,`. The full return block should now read:

```python
    return FeatureSelectionResult(
        selected=features[selected_names],
        similarity_matrix=nmi_matrix,
        cluster_dict=clusters,
        medoid_per_cluster=medoids,
    )
```

- [ ] **Step 5: Run the FULL test suite to confirm both the new test passes AND existing tests still see `nmi_matrix` via the alias**

Run: `pytest tests/test_features.py -q`
Expected: all tests green (including the new `test_similarity_matrix_alias_equivalence`). Every existing test that reads `result.nmi_matrix` now goes through the property and still gets the same array.

- [ ] **Step 6: Stage (no commit)**

Run: `git add src/hmm_core/features.py tests/test_features.py`

Intended commit (left to user): `refactor(features): rename nmi_matrix → similarity_matrix (keep alias)`

---

## Task 4: Add `criterion` parameter + `_dcor_matrix` builder + lazy dcor import

**Files:**
- Modify: `src/hmm_core/features.py`
- Test (new): `tests/test_features.py` (append parametrized tests for both criteria + dcor-specific tests)

- [ ] **Step 1: Add the failing parametrized tests**

In `tests/test_features.py`, append at the end of the file:

```python
# --- dcor criterion ------------------------------------------------------

dcor = pytest.importorskip("dcor")  # whole-module skip if extra not installed


@pytest.mark.parametrize("criterion", ["nmi", "dcor"])
def test_selection_returns_subset_per_criterion(independent_df, criterion):
    result = unsupervised_feature_selection(
        independent_df, n_clusters=3, criterion=criterion
    )
    assert set(result.selected.columns).issubset(set(independent_df.columns))
    assert len(result.selected.columns) == 3


@pytest.mark.parametrize("criterion", ["nmi", "dcor"])
def test_correlated_features_collapse_per_criterion(correlated_df, criterion):
    """A and B are near-duplicates — both criteria must put them in the same
    cluster and keep at most one of them."""
    result = unsupervised_feature_selection(
        correlated_df, n_clusters=4, criterion=criterion
    )
    kept = set(result.selected.columns)
    assert len({"A", "B"} & kept) <= 1
    cluster_of = {
        name: cid
        for cid, names in result.cluster_dict.items()
        for name in names
    }
    assert cluster_of["A"] == cluster_of["B"]


def test_dcor_similarity_matrix_properties(independent_df):
    """dcor matrix must be symmetric, in [0, 1], with 1.0 on the diagonal."""
    p = independent_df.shape[1]
    result = unsupervised_feature_selection(
        independent_df, n_clusters=3, criterion="dcor"
    )
    M = result.similarity_matrix
    assert M.shape == (p, p)
    assert np.allclose(np.diag(M), 1.0)
    assert np.allclose(M, M.T)
    assert M.min() >= 0.0
    assert M.max() <= 1.0


def test_criterion_invalid_value_raises(independent_df):
    with pytest.raises(ValueError, match="criterion"):
        unsupervised_feature_selection(
            independent_df, n_clusters=3, criterion="kendall"
        )
```

- [ ] **Step 2: Run the new tests, verify they FAIL**

Run: `pytest tests/test_features.py -k "criterion or dcor" -v`
Expected: FAIL — the existing function signature does not accept `criterion`, so all four tests will fail with `TypeError: ... unexpected keyword argument 'criterion'` (or similar).

- [ ] **Step 3: Add the `_dcor_matrix` builder to `features.py`**

In `src/hmm_core/features.py`, insert this new private function immediately AFTER `_entropy_diagonal` and BEFORE `_cluster_and_pick_medoids`:

```python
_DCOR_EXTRA_HINT = (
    "criterion='dcor' requires the 'dcor' extra: "
    "pip install \"hmm-studio[dcor]\""
)


def _dcor_matrix(standardized: np.ndarray) -> np.ndarray:
    """Distance-correlation similarity matrix.

    Returns a symmetric ``(p, p)`` matrix with values in ``[0, 1]`` and ``1.0``
    on the diagonal. Uses the ``dcor`` package (Székely, Rizzo & Bakirov 2007).
    """
    try:
        import dcor
    except ImportError as exc:
        raise ImportError(_DCOR_EXTRA_HINT) from exc

    p = standardized.shape[1]
    M = np.zeros((p, p))
    for i in range(p):
        M[i, i] = 1.0
        for j in range(i + 1, p):
            d = float(dcor.distance_correlation(
                standardized[:, i], standardized[:, j]
            ))
            M[i, j] = d
            M[j, i] = d
    return M
```

- [ ] **Step 4: Add the `criterion` parameter and the dcor branch in `unsupervised_feature_selection`**

In the SAME file, modify `unsupervised_feature_selection`'s signature and body. The new signature (keyword-only after `n_clusters` to keep call sites unambiguous):

```python
def unsupervised_feature_selection(
    features: pd.DataFrame,
    n_clusters: int = 10,
    *,
    criterion: str = "nmi",
    n_neighbors: int = 5,
    linkage_method: str = "average",
    jitter_std: float = 1e-8,
    random_state: int = 42,
) -> FeatureSelectionResult:
```

(If any existing code in the project calls this function positionally past `n_clusters`, those call sites must be updated to keyword form. Grep first: `git grep -n "unsupervised_feature_selection(" src/ tests/`. None should pass `n_neighbors` etc. positionally — but verify.)

Then update the body. Right AFTER the existing column/n_vars setup and standardization, BEFORE the `entropy = _entropy_diagonal(...)` line, insert:

```python
    if criterion not in {"nmi", "dcor"}:
        raise ValueError(
            f"criterion must be 'nmi' or 'dcor', got {criterion!r}"
        )

    if criterion == "dcor":
        similarity = _dcor_matrix(standardized)
        medoids, clusters, selected_names = _cluster_and_pick_medoids(
            similarity_matrix=similarity,
            columns=columns,
            n_clusters=n_clusters,
            linkage_method=linkage_method,
        )
        return FeatureSelectionResult(
            selected=features[selected_names],
            similarity_matrix=similarity,
            cluster_dict=clusters,
            medoid_per_cluster=medoids,
        )
```

The existing NMI path (entropy → MI → NMI → call to `_cluster_and_pick_medoids`) stays as the fall-through.

Also extend the docstring's Parameters section : add the `criterion` block in the right alphabetical-ish place (before `n_neighbors`). Concretely insert:

```
    criterion
        Similarity criterion. ``"nmi"`` (default) uses normalised mutual
        information via the sklearn k-NN estimator. ``"dcor"`` uses distance
        correlation (Székely, Rizzo & Bakirov 2007) — deterministic, no
        jitter / k-NN tuning, requires the optional ``dcor`` extra
        (``pip install "hmm-studio[dcor]"``). ``n_neighbors``, ``jitter_std``
        and ``random_state`` are ignored when ``criterion="dcor"``.
```

- [ ] **Step 5: Run the new tests, verify they PASS**

Run: `pytest tests/test_features.py -k "criterion or dcor" -v`
Expected: all 4 new tests PASS. Each parametrized test produces 2 cases (nmi + dcor); the dcor cases require `dcor` installed (Task 1 did this).

- [ ] **Step 6: Run the FULL feature test suite to confirm no regression**

Run: `pytest tests/test_features.py -q`
Expected: every existing test still green; new parametrized + dcor + invalid-criterion tests also green.

- [ ] **Step 7: Stage (no commit)**

Run: `git add src/hmm_core/features.py tests/test_features.py`

Intended commit (left to user): `feat(features): add criterion="dcor" (distance correlation) option`

---

## Task 5: Pass the `criterion` parameter through the prep op

**Files:**
- Modify: `src/hmm_core/prep/ops.py`
- Test: `tests/test_features.py` (one new test for the prep-op passthrough)

- [ ] **Step 1: Add the failing prep-op test**

In `tests/test_features.py`, append at the end of the file:

```python
def test_prep_op_passes_criterion(correlated_df):
    """The select_features_unsupervised prep op forwards `criterion` to the
    underlying selector."""
    op = OPS["select_features_unsupervised"]
    out = op(correlated_df, n_clusters=4, criterion="dcor")
    # output is a DataFrame with 4 columns, A and B collapse
    assert out.shape[1] == 4
    kept = set(out.columns)
    assert len({"A", "B"} & kept) <= 1
```

- [ ] **Step 2: Run the new test, verify it FAILS**

Run: `pytest tests/test_features.py::test_prep_op_passes_criterion -v`
Expected: FAIL with `TypeError: select_features_unsupervised() got an unexpected keyword argument 'criterion'`.

- [ ] **Step 3: Add `criterion` to the prep-op signature and forward it**

In `src/hmm_core/prep/ops.py`, find this exact block (current function definition, lines ~215-248):

```python
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
```

Replace it with:

```python
@register_op("select_features_unsupervised")
def select_features_unsupervised(
    df: pd.DataFrame,
    *,
    n_clusters: int = 10,
    criterion: str = "nmi",
    n_neighbors: int = 5,
    linkage_method: str = "average",
    jitter_std: float = 1e-8,
    random_state: int = 42,
) -> pd.DataFrame:
    """Keep one medoid feature per similarity cluster (unsupervised selection).

    Thin recipe-friendly wrapper around
    :func:`hmm_core.features.unsupervised_feature_selection` : clusters the
    candidate columns by the chosen criterion and returns only the selected
    (decorrelated) subset of columns — a ``df -> df`` op.

    ``criterion`` selects the similarity measure : ``"nmi"`` (default) uses
    normalised mutual information via the sklearn k-NN estimator ;
    ``"dcor"`` uses distance correlation (requires the optional ``dcor`` extra :
    ``pip install "hmm-studio[dcor]"``). When ``criterion="dcor"``,
    ``n_neighbors``, ``jitter_std`` and ``random_state`` are ignored.

    The rich metadata (similarity matrix, clusters) is not exposed in the
    pipeline ; call ``unsupervised_feature_selection`` directly to inspect it.
    NaN rows must be dropped upstream (e.g. a preceding ``dropna`` step) — the
    k-NN MI estimator needs clean input.
    """
    # Imported lazily: pulls sklearn/scipy, which we keep out of the
    # module-load path for the prep package.
    from hmm_core.features import unsupervised_feature_selection

    return unsupervised_feature_selection(
        df,
        n_clusters=n_clusters,
        criterion=criterion,
        n_neighbors=n_neighbors,
        linkage_method=linkage_method,
        jitter_std=jitter_std,
        random_state=random_state,
    ).selected
```

(Only two real changes: `criterion: str = "nmi"` added to the signature in alphabetical-ish position before `n_neighbors`, and `criterion=criterion,` added to the forwarded call. The docstring is rewritten to explain the new parameter.)

- [ ] **Step 4: Run the new test, verify it PASSES**

Run: `pytest tests/test_features.py::test_prep_op_passes_criterion -v`
Expected: PASS.

- [ ] **Step 5: Run the FULL test suite to confirm no regression**

Run: `pytest tests/test_features.py -q`
Expected: all green.

- [ ] **Step 6: Stage (no commit)**

Run: `git add src/hmm_core/prep/ops.py tests/test_features.py`

Intended commit (left to user): `feat(prep): forward criterion in select_features_unsupervised op`

---

## Task 6: Update Academy lesson 13 with the dcor section

**Files:**
- Modify: `src/hmm_studio/frontend/src/lessons/lesson-13-choosing-features.tsx`

- [ ] **Step 1: Insert a new section before "Where to learn more"**

Open `src/hmm_studio/frontend/src/lessons/lesson-13-choosing-features.tsx`. Locate the existing `<h2 ...>Where to learn more</h2>` heading. Insert the following block IMMEDIATELY BEFORE that heading (it becomes a new section just before the closing material):

```tsx
      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Alternative criterion : distance correlation
      </h2>
      <p className="text-slate-700 mb-4">
        NMI is not the only way to measure shared information. The selector also
        accepts <code className="bg-slate-100 px-1 rounded text-sm">criterion="dcor"</code>,
        which uses <strong>distance correlation</strong> (Székely, Rizzo &amp;
        Bakirov 2007) instead. dcor is :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Deterministic.</strong> A closed-form functional of pairwise
          distances. No k-NN estimator, no jitter, no{" "}
          <code className="bg-slate-100 px-1 rounded text-sm">random_state</code>{" "}
          to worry about.
        </li>
        <li>
          <strong>Characterises independence.</strong>{" "}
          <code className="bg-slate-100 px-1 rounded text-sm">dcor(X, Y) = 0</code>{" "}
          iff X and Y are independent (not just linearly uncorrelated).
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        The trade-off : dcor is{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">O(n²)</code> per feature
        pair, against{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">~O(n log n)</code> for the
        k-NN MI estimator. On very large samples NMI is faster ; on small-to-medium
        samples dcor is the safer choice because there is nothing to tune and nothing
        stochastic to seed.
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`# Install the optional extra first :
#   pip install "hmm-studio[dcor]"
result = unsupervised_feature_selection(df, n_clusters=8, criterion="dcor")`}</code>
      </pre>
      <p className="text-slate-700 mb-4">
        The YAML pipeline op exposes the same parameter :
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`steps:
  - op: dropna
  - op: select_features_unsupervised
    n_clusters: 8
    criterion: dcor`}</code>
      </pre>

```

(Keep one blank line between the new `</pre>` and the existing `<h2 ...>Where to learn more</h2>` line.)

- [ ] **Step 2: Lint + build**

Run (from `src/hmm_studio/frontend/`): `npm run lint && npm run build`
Expected: both exit 0. The build should still report 708 modules (same as after sub-project B — the lesson is plain TSX content, no new component).

- [ ] **Step 3: Stage (no commit)**

Run (from repo root): `git add src/hmm_studio/frontend/src/lessons/lesson-13-choosing-features.tsx`

Intended commit (left to user): `docs(academy): lesson 13 — add dcor alternative criterion`

---

## Task 7: Add Székely-Rizzo-Bakirov 2007 to the central bibliography

**Files:**
- Modify: `docs/sources/academy-references.md`

- [ ] **Step 1: Insert the Tier-3 entry**

Open `docs/sources/academy-references.md`. Find the section heading `## Tier 3 — Variant-specific`. Locate the end of that section — the LAST `### ...` entry under Tier 3 (which, after sub-project B, is the new `### Rothfuss et al. ICLR 2020 — ...` entry inserted there in Task 5 of B's plan). Locate the `---` divider that closes Tier 3 (it sits BEFORE the `## Tier 4` heading at line ~256). Insert IMMEDIATELY BEFORE that `---` divider (and after the last `### ...` block, with one blank line of separation):

```markdown
### Székely, Rizzo & Bakirov 2007 — *Measuring and testing dependence by correlation of distances*

Gábor J. Székely, Maria L. Rizzo, Nail K. Bakirov. *Annals of Statistics* 35(6),
2769–2794.

Introduces distance correlation, a measure that characterises independence
(``dcor(X, Y) = 0`` iff X and Y are independent, not merely uncorrelated) and
works on continuous and categorical data without density estimation. The Python
``dcor`` package implements it for practical use. Underlies the
``criterion="dcor"`` option of ``unsupervised_feature_selection``.

— **PDF** : <https://projecteuclid.org/journals/annals-of-statistics/volume-35/issue-6/Measuring-and-testing-dependence-by-correlation-of-distances/10.1214/009053607000000505.full>

```

- [ ] **Step 2: Update the lesson 13 row in the per-lesson citation table**

Find the table heading `## How each Academy lesson cites these` and the row whose first column reads `| 13. *Choosing features for your HMM* |` (it currently lists `Kraskov et al. 2004 + scikit-learn ...` per the original spec, but the actual current cell may differ — read the actual row). Replace the second cell to include the new reference, keeping any existing references. The updated row:

```markdown
| 13. *Choosing features for your HMM* | Kraskov et al. 2004 (NMI), Székely-Rizzo-Bakirov 2007 (dcor) |
```

If the existing cell wording differs, preserve the existing wording and append `, Székely-Rizzo-Bakirov 2007 (dcor)` at the end. The point is to add the dcor reference, not to rewrite the row.

- [ ] **Step 3: Sanity-check**

Run (from repo root): `grep -c "009053607000000505" docs/sources/academy-references.md`
Expected: `1` — the PDF URL appears exactly once (in the new entry).

Run: `grep -c "Székely" docs/sources/academy-references.md`
Expected: `≥ 2` — once in the new entry's heading + once in the table row (possibly more if other entries reference it).

- [ ] **Step 4: Stage (no commit)**

Run: `git add docs/sources/academy-references.md`

Intended commit (left to user): `docs(academy): add Székely et al. 2007 (distance correlation) reference`

---

## Task 8: Append a dated update to the existing 2026-05-27 spec

**Files:**
- Modify: `docs/specs/2026-05-27-unsupervised-feature-selection.md`

This preserves the historicization rule from the workspace CLAUDE.md (specs are append-only).

- [ ] **Step 1: Append the update section at the end of the file**

Open `docs/specs/2026-05-27-unsupervised-feature-selection.md`. At the very end of the file (after the last existing line), append:

```markdown

## Update 2026-05-28 — `dcor` as an alternative criterion

`unsupervised_feature_selection` now accepts a `criterion` parameter taking
`"nmi"` (default, unchanged behaviour) or `"dcor"` (distance correlation, via
the optional `dcor` extra). Motivation : the NMI k-NN estimator is sensitive
to jitter and to the choice of `k`, and Nathan's parallel crypto research
switched empirically from MI/linfoot to `dcor.distance_correlation` for
reproducibility. `dcor` is deterministic, requires no jitter, and characterises
independence (`dcor(X, Y) = 0` iff X⊥Y), at the cost of `O(n²)` per feature
pair (vs k-NN MI's `~O(n log n)`).

Key API decisions :

- New parameter is keyword-only after `n_clusters`. Default `"nmi"` preserves
  the full backward-compatible signature.
- `dcor` is declared as an *optional* extra `[dcor]` in `pyproject.toml`,
  following the existing `[bayesian]` pattern. `criterion="dcor"` raises an
  `ImportError` with an actionable install message if the extra is missing.
- The shared clustering+medoid pipeline was extracted into a private helper
  `_cluster_and_pick_medoids(similarity_matrix, columns, n_clusters,
  linkage_method)` so both criteria feed the same selection logic.
- `FeatureSelectionResult.nmi_matrix` was renamed to `similarity_matrix` (the
  name was inappropriate for non-NMI criteria). A `@property nmi_matrix`
  returns the same array, preserving backward compatibility for callers using
  the legacy attribute name.
- The prep op `select_features_unsupervised` gained the same `criterion`
  field, exposed in YAML pipelines.

See implementation plan : `docs/superpowers/plans/2026-05-28-features-dcor-criterion.md`
and design : `docs/superpowers/specs/2026-05-28-features-dcor-criterion-design.md`.

Academy lesson 13 was updated with an "Alternative criterion : distance
correlation" section explaining the trade-off ; `docs/sources/academy-references.md`
gained a Tier-3 entry for Székely, Rizzo & Bakirov 2007.
```

- [ ] **Step 2: Sanity-check**

Run (from repo root): `grep -c "Update 2026-05-28" docs/specs/2026-05-27-unsupervised-feature-selection.md`
Expected: `1`.

- [ ] **Step 3: Stage (no commit)**

Run: `git add docs/specs/2026-05-27-unsupervised-feature-selection.md`

Intended commit (left to user): `docs(spec): append dcor-criterion update to feature-selection spec`

---

## Task 9: End-to-end verification

**Files:**
- None modified. Final whole-project check.

- [ ] **Step 1: Full Python test suite (focused on the touched module + adjacent)**

Run (from repo root): `pytest tests/test_features.py -q`
Expected: every test green (the pre-existing tests + the new alias / parametrized / dcor-specific / invalid-criterion / prep-op tests, totalling several more than the pre-change baseline).

- [ ] **Step 2: Full frontend build**

Run (from `src/hmm_studio/frontend/`): `npm run build`
Expected: exit 0. (No new component was added — same 708 modules as after sub-project B.)

- [ ] **Step 3: Confirm staged set**

Run (from repo root): `git status --short`
Expected output should include (only the seven files this plan modifies, in addition to whatever sub-project B left staged on the same branch):

```
M  docs/sources/academy-references.md
M  docs/specs/2026-05-27-unsupervised-feature-selection.md
M  pyproject.toml
M  src/hmm_core/features.py
M  src/hmm_core/prep/ops.py
M  src/hmm_studio/frontend/src/lessons/lesson-13-choosing-features.tsx
M  tests/test_features.py
```

(Plus the B staged set : `lesson-14-comparing-models.tsx`, `lesson-15-choosing-emission.tsx`, `lessons/index.ts`, and the B-side updates to `academy-references.md`.)

- [ ] **Step 4: Confirm HEAD unchanged (no commit was made by the implementer)**

Run: `git log --oneline -1`
Expected: same HEAD SHA as before this plan ran. The user commits on their schedule.

(No commit on this task — the user commits the staged set.)

---

## Notes
- **No new module file was created.** All backend changes live inside the existing `src/hmm_core/features.py` (refactor + new helper + new criterion branch) and `src/hmm_core/prep/ops.py` (one-parameter passthrough).
- **No new test file was created.** All new tests append to `tests/test_features.py`, parametrizing where convenient and adding dcor-specific assertions where the parametrization doesn't fit cleanly.
- **No new component file** in the frontend. Lesson 13 grows by ~30 lines.
- **dcor version `>=0.6`** is the minimum that exposes `distance_correlation` as a stable public API. The pin is loose to let users get bugfixes.
- **The branch may already carry sub-project B's staged set.** The seven C files are independent from B's four files, so the user can split commits at will (e.g., `git commit -m "B" -- <B files>` followed by `git commit -m "C" -- <C files>`).
