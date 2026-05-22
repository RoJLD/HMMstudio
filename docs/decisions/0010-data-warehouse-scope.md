# ADR-0010: Data warehouse scope (Phase B.10)

**Date**: 2026-05-22
**Status**: Accepted
**Authors**: Robin Denis

## Context

The studio's existing data upload (Phase B.5) is one-shot: upload a CSV,
preview it, use it for ONE fit. For a researcher juggling multiple
datasets across multiple topology / hyperparameter combinations, this is
real friction — every dataset must be re-uploaded, and there is no
memory of "what this dataset is" between sessions.

A solution exists in the data-engineering ecosystem: DVC, MLflow, lakeFS,
Delta Lake. They are mature, well-funded, and cover much more than HMM
needs.

## Decision

Build a **read-only directory explorer** specialised for HMM datasets.
Specifically NOT a data versioning, lineage, or remote-storage system.

Scope IN:
- Designate ONE local directory as the "warehouse" (via env var
  `HMM_STUDIO_WAREHOUSE_PATH` for the MVP, settings UI later).
- Auto-scan with format dispatch: CSV, TSV, Parquet, Feather, JSON, JSONL,
  Excel (xlsx + xls).
- Per-dataset sidecar YAML (`<dataset>.hmm.yaml`) for optional provenance
  and column roles. Sidecars are opt-in; absent sidecars give auto-detected
  metadata.
- Upload endpoint to write a new dataset into the warehouse.
- Path-traversal protection on all `rel_path` endpoints.

Scope OUT (explicit non-goals):
- **Versioning**: no git-like history of datasets. Users with that need
  put `git init` or DVC in their warehouse directly.
- **Remote storage**: no S3 / GCS / Azure Blob. The warehouse is a local
  filesystem path. Period.
- **Lineage / DAG**: no tracking of "this fit used dataset X version Y".
  The fit-job DB already records `dataset_id` per job; that is the level
  of linkage we ship.
- **Multi-warehouse**: one path per studio instance. Users with multiple
  projects use multiple studio instances or symlink trees.
- **Full-text indexing / search**: list + format-filter is enough at the
  scales we target (<100 datasets).

## Alternatives considered

- **Database-backed metadata** (a dataset table in SQLite): rejected.
  Forces a database mutation on every file added; loses the "data lives
  in the filesystem" property; complicates Docker / volume backup. Sidecar
  YAMLs are simpler and version-controllable alongside the data.
- **DVC integration**: rejected for MVP. DVC is heavyweight; users who
  want it already have it; we would inherit its semantics and edge cases.
- **Embedding a data catalog (DataHub, OpenMetadata)**: massively
  over-scoped; the catalog category is its own multi-year product.

## Consequences

### Positive
- Friction reduced from "upload → fit → discard" to "select → fit → keep".
- Sidecar YAMLs are diffable in git; metadata travels with the data.
- Backend is ~200 lines + 12 tests; no new infrastructure dependencies
  beyond `openpyxl` for Excel reading.
- Aligns with hmm-studio's local-first philosophy (cf. ADR-0002).

### Negative
- No history: if a dataset is overwritten, the old version is lost. We
  document this explicitly in the warehouse panel UI.
- Sidecar YAML format is opinionated; users with their own metadata
  conventions must adapt. We keep the schema lightweight to minimise
  this friction.
- Path traversal must be defended at every endpoint that takes a
  `rel_path` parameter. Tested explicitly.

### Settings UX

The MVP uses an env var `HMM_STUDIO_WAREHOUSE_PATH`. A full settings UI
(input field in a settings panel) is deferred to a follow-up (B.10.x);
the env var is sufficient for the docker-compose deployment.

## Revisit triggers

- A user has a real workflow that requires versioning or remote storage
  → consider integrating with DVC rather than building it ourselves.
- The warehouse routinely contains >500 datasets and scan time becomes
  perceptible → add real caching (Redis or DB-backed scan results).
- Multi-user / SaaS pivot → reconsider local-only assumption; warehouse
  becomes per-user with auth.

## Pointers

- `src/hmm_studio/server/warehouse.py`
- `src/hmm_studio/server/app.py` (the 6 endpoints under `/api/warehouse/*`)
- `tests/studio/test_warehouse.py` (12+ tests)
- Phase B.10 full spec: `docs/specs/2026-05-22-phase-b10-data-warehouse.md`
- ADR-0002 (B stack — local-first principle)
