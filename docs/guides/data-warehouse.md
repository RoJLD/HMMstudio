# Data warehouse

The studio's **Data warehouse** turns a local directory into a first-class
dataset library. You point hmm-studio at a folder on your machine, it scans
for supported tabular formats, picks up optional sidecar metadata, and lets
you promote any file straight into a fit run.

The wedge here is narrow on purpose: **no remote storage, no versioning,
no DVC-style lineage**. The rationale for staying small is captured in
[ADR-0010](../decisions/0010-data-warehouse-scope.md). When you need true
data versioning, run DVC upstream — hmm-studio reads the materialised file
either way.

## Pourquoi ?

Before B.10 the Data tab only accepted one-shot uploads. Comparing five
datasets across three topologies meant re-uploading the same CSVs every
session and losing the "what is this file again?" context in between. The
warehouse solves three concrete frictions:

- **No more re-uploading.** The studio reads the file in place; nothing
  is copied unless you explicitly promote it.
- **Metadata travels with the file.** A sidecar `*.hmm.yaml` next to the
  dataset persists provenance, column roles, and free-form notes. Git it
  if you want; rsync it; share it.
- **Stateless server.** The filesystem is the source of truth. No
  warehouse table to migrate, no orphaned entries when you `rm` a file.

## Configure the warehouse path

Two ways to tell the studio where your warehouse lives. Precedence:
**database override > environment variable > unset**.

### Environment variable (default)

```powershell
$env:HMM_STUDIO_WAREHOUSE_PATH = "C:\Users\rdenis\Datasets\hmm"
hmm-studio serve
```

```bash
export HMM_STUDIO_WAREHOUSE_PATH="$HOME/datasets/hmm"
hmm-studio serve
```

The variable is read at request time, not at boot. You can change it and
restart with no migration step.

### `/settings` page (override the env var)

If you set `warehouse_path` via the settings UI or `PUT /api/settings`, the
DB value wins over the env var. Setting it to an empty string clears the
override and falls back to the env var. See the
[Settings guide](settings.md) for the full precedence table.

!!! tip "Inspect the resolved value"
    `GET /api/settings` returns both the resolved `warehouse_path` and a
    `warehouse_path_source` field (`db`, `env`, or `unset`) so you can tell
    at a glance which layer is winning.

## Supported formats

Single-dispatch by extension. Drop a file with one of these suffixes into
the warehouse and it shows up on the next scan.

| Extension | Reader |
|---|---|
| `.csv` | `pandas.read_csv` |
| `.tsv` | `pandas.read_csv(sep="\t")` |
| `.parquet` | `pandas.read_parquet` |
| `.feather` | `pandas.read_feather` |
| `.json` | `pandas.read_json(orient="records")` |
| `.jsonl` | `pandas.read_json(orient="records", lines=True)` |
| `.xlsx`, `.xls` | `pandas.read_excel` |

Anything else is silently skipped during the scan. Hidden files and
directories (anything starting with `.`) are also ignored.

## Sidecar `.hmm.yaml`

Next to `btc_2024.csv`, drop `btc_2024.csv.hmm.yaml`. The studio reads it,
displays the metadata in the warehouse sidebar, and uses the column roles
to pre-fill the fit launcher.

```yaml
schema_version: 1
name: "BTC daily 2024"
description: "BTC/USD daily close + 4 features for regime modelling"
provenance:
  source_url: "https://example.com/btc.csv"
  uploaded_at: "2026-05-22T15:30:00Z"
  uploaded_by: "robin"
columns:
  - name: timestamp
    role: index
    dtype: datetime
  - name: log_return
    role: observation
    dtype: float64
  - name: realized_vol
    role: covariate
    dtype: float64
  - name: funding_rate
    role: covariate
    dtype: float64
notes: |
  Vol computed on a 20-day window.
  Funding rate normalised.
```

Sidecars are **optional**. A dataset without one still works — you just
lose the role hints and the provenance trail.

The supported column `role` values today are:

- `index` — typically a timestamp; not used as a feature
- `observation` — passed to the emission model
- `covariate` — passed as `Z` to NHMM / GMM-NHMM / Factorial NHMM

## The "Use for fit" flow

The end-to-end path from warehouse file to fitted model:

1. Open the **Data** tab. The warehouse sidebar lists files under
   `warehouse_path` (recursive).
2. Click a file. The right panel shows a preview (first 10 rows by
   default), inferred dtypes, sidecar metadata if any.
3. Click **Edit sidecar metadata** to fill in column roles. The form
   round-trips to the YAML on disk.
4. Click **Use for fit →**. The studio calls
   `POST /api/warehouse/{rel_path}/promote`, which parses the file once,
   stores it as a canonical Dataset row, and navigates you to the Fit
   page with the dataset preselected.

The original warehouse file is left untouched. The studio's internal
`uploads_dir` gets a CSV copy as the canonical form — that's intentional
so the same fit can be re-run later even if the warehouse path moves.

## Programmatic uploads

If you'd rather drop files in from a script, `POST /api/warehouse/upload`
accepts a multipart file plus an optional `subdir` query string:

```bash
curl -X POST http://localhost:8000/api/warehouse/upload \
    -F "file=@btc_2024.csv" \
    -F "subdir=btc/daily"
```

The file lands at `<warehouse_path>/btc/daily/btc_2024.csv`. The
endpoint refuses uploads larger than 200 MB and rejects any `subdir`
that escapes the warehouse root.

## Security: path traversal

Every warehouse endpoint that takes a `rel_path` runs it through
`safe_resolve` before touching the filesystem:

```python
def safe_resolve(warehouse_root: Path, rel_path: str) -> Path:
    warehouse_root = warehouse_root.resolve()
    full = (warehouse_root / rel_path).resolve()
    try:
        full.relative_to(warehouse_root)
    except ValueError:
        raise ValueError(f"path traversal blocked: {rel_path}")
    return full
```

Without this, `GET /api/warehouse/../../../etc/passwd/preview` would
escape the configured root. There is a regression test
(`tests/studio/test_warehouse.py::test_path_traversal_blocked`) that locks
the behaviour in.

!!! warning "Local-first, not multi-tenant"
    The warehouse is designed for a single local user. Pointing it at a
    shared mount and exposing the studio's port over the network would
    let any caller list, preview, and **upload into** that directory.
    Bind to localhost or put auth in front.

## Cache behaviour

The scan result is cached in-process with a 5-second TTL. Three triggers
invalidate it:

- An explicit `POST /api/warehouse/refresh`.
- An upload via `POST /api/warehouse/upload`.
- An update to `warehouse_path` via `PUT /api/settings`.

Nothing else is cached — sidecar reads and previews hit the filesystem
every time. With < 100 datasets that's fast enough; we can revisit if
someone hits a real scale wall.

## Limites

- Filesystem source of truth. Renaming a file via `mv` is fine; the next
  scan picks it up. There is no rename API.
- No tags / search / facets. Use directory structure for organisation.
- Sidecar schema is **lightly validated** — only `schema_version` and a
  handful of free-form fields are enforced. We chose flexibility over
  rigid schemas at this stage.
- No `Δ`-aware re-scan. The full directory is walked on each cache miss.
  For < 100 datasets the latency is invisible.

## Voir aussi

- [Phase B.10 spec](../specs/2026-05-22-phase-b10-data-warehouse.md) —
  full design + test matrix.
- [ADR-0010](../decisions/0010-data-warehouse-scope.md) — why no
  versioning, why local-only, why sidecar YAML.
- [Settings guide](settings.md) — the `/settings` page and its
  precedence model.
