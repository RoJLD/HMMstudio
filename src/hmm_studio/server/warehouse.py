"""Local data warehouse: directory-based dataset explorer for hmm-studio.

The user points the studio at a host directory (via env var
``HMM_STUDIO_WAREHOUSE_PATH``); the warehouse module scans it for supported
dataset formats (CSV, Parquet, JSON/JSONL, Excel, Feather, TSV), exposes
their metadata + preview, and supports optional sidecar YAML files
``<dataset>.hmm.yaml`` carrying provenance / column roles / notes.

Read-only by default; the upload endpoint writes new datasets into the
warehouse. Sidecar edits are also supported.

Security: ``safe_resolve`` blocks path traversal. Without it,
``GET /api/warehouse/../../../etc/passwd/preview`` would escape the
warehouse root.

This module is filesystem-only (no DB), so it is stateless from the
server's perspective. A tiny in-process cache speeds up repeated scans.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

SIDECAR_SUFFIX = ".hmm.yaml"

# Encoding cascade tried in order for CSV / TSV reads. UTF-8 covers
# modern data, ISO-8859-1 covers older Latin-1 dumps (and never raises
# UnicodeDecodeError — it accepts any byte), cp1252 is the Windows
# default for French / Western European exports.
_CSV_ENCODING_CASCADE = ("utf-8", "cp1252", "iso-8859-1")


def _read_csv_with_encoding_fallback(path: Path, *, sep: str = ",") -> pd.DataFrame:
    """Read a CSV / TSV with an encoding cascade fallback.

    Tries UTF-8 first, then cp1252, then ISO-8859-1 on ``UnicodeDecodeError``.
    If a ``<path>.hmm.yaml`` sidecar exposes ``provenance.encoding: <enc>``,
    that encoding is attempted first (the standard cascade is the fallback
    if even the user's hint fails).

    Raises ``ValueError`` listing every attempted encoding when nothing works.
    """
    candidates: list[str] = []
    sidecar_meta = load_sidecar(path)
    if sidecar_meta is not None:
        provenance = sidecar_meta.get("provenance")
        if isinstance(provenance, dict):
            hint = provenance.get("encoding")
            if isinstance(hint, str) and hint:
                candidates.append(hint)
    for enc in _CSV_ENCODING_CASCADE:
        if enc not in candidates:
            candidates.append(enc)

    errors: list[str] = []
    for enc in candidates:
        try:
            return pd.read_csv(path, sep=sep, encoding=enc)
        except UnicodeDecodeError as e:
            errors.append(f"{enc}: {e.reason}")
            continue
    raise ValueError(
        f"could not decode {path.name} ; tried encodings {candidates}. "
        f"Errors: {errors}"
    )


# ---------------------------------------------------------------------------
# Format dispatch
# ---------------------------------------------------------------------------

FORMAT_READERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    ".csv": _read_csv_with_encoding_fallback,
    ".tsv": lambda p: _read_csv_with_encoding_fallback(p, sep="\t"),
    ".parquet": pd.read_parquet,
    ".feather": pd.read_feather,
    ".json": lambda p: pd.read_json(p, orient="records"),
    ".jsonl": lambda p: pd.read_json(p, orient="records", lines=True),
    ".xlsx": pd.read_excel,
    ".xls": pd.read_excel,
}


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in FORMAT_READERS


def read_dataset(path: Path) -> pd.DataFrame:
    """Single-dispatch dataset read by extension. Raises ValueError on unknown format."""
    suffix = path.suffix.lower()
    reader = FORMAT_READERS.get(suffix)
    if reader is None:
        raise ValueError(f"unsupported format: {suffix}. Supported: {sorted(FORMAT_READERS)}")
    return reader(path)


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def safe_resolve(warehouse_root: Path, rel_path: str) -> Path:
    """Resolve ``rel_path`` inside ``warehouse_root``. Raises ValueError on traversal."""
    warehouse_root = warehouse_root.resolve()
    full = (warehouse_root / rel_path).resolve()
    # Python 3.9+: Path.is_relative_to
    try:
        full.relative_to(warehouse_root)
    except ValueError:
        raise ValueError(f"path traversal blocked: {rel_path}")
    return full


# ---------------------------------------------------------------------------
# Scan + sidecar
# ---------------------------------------------------------------------------


@dataclass
class DatasetEntry:
    rel_path: str
    size_bytes: int
    modified_at: datetime
    format: str
    has_sidecar: bool

    def to_dict(self) -> dict:
        return {
            "rel_path": self.rel_path,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at.isoformat(),
            "format": self.format,
            "has_sidecar": self.has_sidecar,
        }


def scan_warehouse(root: Path) -> list[DatasetEntry]:
    """Recursively scan root, return one entry per supported dataset file.

    Skips:
        - directories
        - sidecar files (``*.hmm.yaml``)
        - files with unsupported extensions
        - hidden files / dirs (starting with ``.``)
    """
    if not root.exists() or not root.is_dir():
        return []
    entries: list[DatasetEntry] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        # Skip hidden anywhere in the path
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.name.endswith(SIDECAR_SUFFIX):
            continue
        if not is_supported(path):
            continue
        stat = path.stat()
        sidecar_path = path.parent / f"{path.name}{SIDECAR_SUFFIX}"
        entries.append(
            DatasetEntry(
                rel_path=str(path.relative_to(root)).replace("\\", "/"),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                format=path.suffix.lower().lstrip("."),
                has_sidecar=sidecar_path.exists(),
            )
        )
    return entries


def load_sidecar(dataset_path: Path) -> dict | None:
    """Read the sidecar YAML next to ``dataset_path``; returns None if absent."""
    sidecar = dataset_path.parent / f"{dataset_path.name}{SIDECAR_SUFFIX}"
    if not sidecar.exists():
        return None
    raw = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def write_sidecar(dataset_path: Path, meta: dict) -> None:
    """Write the sidecar YAML next to ``dataset_path``. Overwrites if it exists."""
    sidecar = dataset_path.parent / f"{dataset_path.name}{SIDECAR_SUFFIX}"
    sidecar.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")


def preview(dataset_path: Path, n: int = 10) -> pd.DataFrame:
    """Return the first ``n`` rows of the dataset."""
    df = read_dataset(dataset_path)
    return df.head(n)


# ---------------------------------------------------------------------------
# Cache (tiny, in-process)
# ---------------------------------------------------------------------------


@dataclass
class _ScanCache:
    """Tiny TTL cache for the warehouse scan. Single-process only."""

    ttl_seconds: float = 5.0
    _last_root: Path | None = field(default=None)
    _last_scan_at: float = field(default=0.0)
    _last_entries: list[DatasetEntry] = field(default_factory=list)

    def get_or_scan(self, root: Path) -> list[DatasetEntry]:
        now = time.monotonic()
        if (
            self._last_root is not None
            and self._last_root == root
            and (now - self._last_scan_at) < self.ttl_seconds
        ):
            return self._last_entries
        entries = scan_warehouse(root)
        self._last_root = root
        self._last_scan_at = now
        self._last_entries = entries
        return entries

    def invalidate(self) -> None:
        self._last_root = None
        self._last_scan_at = 0.0
        self._last_entries = []


_GLOBAL_CACHE = _ScanCache()


def get_scan_cache() -> _ScanCache:
    return _GLOBAL_CACHE
