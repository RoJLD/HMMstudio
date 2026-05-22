# Phase B.10 — Data warehouse local + multi-format : spec

**Date** : 2026-05-22
**Auteur** : Robin Denis (avec architecte-CEO framing)
**Status** : SPEC DRAFTED · prêt à implémenter (use case Robin direct)
**Effort estimé** : 3-4 jours
**Prérequis durs** : B (web UI socle, livré pour l'essentiel)

> Document de spec. Pour le contexte stratégique, voir
> [docs/roadmap.md § Phase B.10](../roadmap.md).

---

## 1. Contexte et motivation

### Le besoin

Aujourd'hui le tab Data du studio web (livré en B.5) permet d'uploader un
CSV à la fois et de le lier à un fit. Pour un chercheur qui :
- compare plusieurs datasets,
- réutilise un dataset à travers plusieurs topologies / configurations,
- veut une trace de provenance,

c'est de la friction réelle. Chaque dataset doit être uploadé séparément
et on perd la mémoire de "ce que c'est" entre les sessions.

### Le scope qu'on **n'attaque PAS**

Ce besoin glisse vers DVC / MLflow / lakeFS / Delta Lake territoire. **On
ne va pas là.** Trois raisons :
1. Ce sont des projets matures bien financés ; on n'a pas la capacité de
   les concurrencer ni l'intérêt.
2. Le wedge `hmm-studio` est **modélisation HMM**, pas data engineering.
3. Les utilisateurs qui ont besoin de versioning formel auront déjà DVC
   en amont. On laisse les data live où ils sont.

### Le scope qu'on **attaque**

Un **explorateur de fichiers spécialisé pour datasets HMM** :
- Désigne un répertoire local comme "warehouse"
- Scan + métadonnées + preview + sélection rapide depuis le studio
- Auto-détection format (CSV/parquet/JSON/Excel/feather)
- Sidecar `.hmm.yaml` à côté de chaque dataset pour notes / provenance

C'est environ ~3-4 jours d'effort pour une feature qui réduit
significativement la friction.

## 2. Architecture proposée

### Configuration

Le warehouse path est stocké dans les settings utilisateur (table
`SettingsRow` dans la DB SQLModel existante du studio) :

```yaml
# Stocké en DB ou config file selon la convention déjà en place dans B
user_settings:
  warehouse_path: "C:/Users/rdenis/Datasets/hmm/"
  warehouse_auto_scan: true              # rescan à chaque visite du tab Data
  warehouse_supported_formats:           # whitelist, default ci-dessous
    - csv
    - parquet
    - json
    - jsonl
    - xlsx
    - feather
```

### Modèle de données (additif au backend B)

Pas de nouvelle table — uniquement un nouveau endpoint qui scanne le
filesystem à la volée. **Stateless** côté serveur.

### Endpoints REST

```
GET  /api/warehouse                # liste fichiers + meta (taille, modif, format)
POST /api/warehouse/refresh        # force re-scan (cache invalidation)
GET  /api/warehouse/{rel_path}/preview?n=10   # preview N lignes
GET  /api/warehouse/{rel_path}/meta           # metadata sidecar + auto-détectées
PUT  /api/warehouse/{rel_path}/meta           # update sidecar yaml
POST /api/warehouse/upload                    # upload un nouveau dataset
```

### Sidecar `.hmm.yaml` (format)

À côté de chaque dataset (e.g. `btc_2024.csv` → `btc_2024.csv.hmm.yaml`) :

```yaml
schema_version: 1
name: "BTC daily 2024"
description: "BTC/USD daily close + 4 features for regime modeling"
provenance:
  source_url: "https://example.com/btc.csv"   # ou local note
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
  - name: volume_z
    role: covariate
    dtype: float64
notes: |
  Vol calculée sur fenêtre 20 jours.
  Funding rate normalisé.
```

Les sidecar sont **optionnels** : un dataset sans sidecar fonctionne
toujours, juste avec les métadonnées auto-détectées (rows, cols, dtypes).

### Détection format

Single dispatch sur extension :

```python
FORMAT_READERS = {
    ".csv":     pd.read_csv,
    ".tsv":     lambda p: pd.read_csv(p, sep="\t"),
    ".parquet": pd.read_parquet,
    ".feather": pd.read_feather,
    ".json":    lambda p: pd.read_json(p, orient="records"),
    ".jsonl":   lambda p: pd.read_json(p, orient="records", lines=True),
    ".xlsx":    pd.read_excel,
    ".xls":     pd.read_excel,
}

def read_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    reader = FORMAT_READERS.get(suffix)
    if reader is None:
        raise ValueError(
            f"unsupported format: {suffix}. "
            f"Supported: {sorted(FORMAT_READERS)}"
        )
    return reader(path)
```

~80 LOC total pour 8 formats.

## 3. Frontend (tab Data étendu)

### Layout proposé

```
┌──────────────────────────────────────────────────────────────┐
│ Data                                                          │
├──────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌──────────────────────────────┐   │
│ │ Warehouse           │  │ Preview                       │   │
│ │ 📁 /Datasets/hmm/  │  │  timestamp  log_return  vol   │   │
│ │  📄 btc_2024.csv   │  │  2024-01-01  -0.012   0.018  │   │
│ │  📄 eth_2024.parq  │  │  2024-01-02   0.024   0.021  │   │
│ │  📄 sp500.xlsx     │  │  2024-01-03   0.015   0.019  │   │
│ │  📂 archive/       │  │  ...                           │   │
│ │   📄 btc_2023.csv  │  │                                │   │
│ │                     │  │ Rows: 252  Cols: 5            │   │
│ │ [Upload new file]  │  │ Size: 12.4 KB  Modif: 2 days  │   │
│ │ [Refresh]          │  │                                │   │
│ │                     │  │ [Edit sidecar metadata]       │   │
│ │ Settings:          │  │ [Use for fit →]               │   │
│ │  path: /Datasets   │  └──────────────────────────────┘   │
│ │  ...               │                                       │
│ └─────────────────────┘                                      │
└──────────────────────────────────────────────────────────────┘
```

### Composants React (additifs)

- `<WarehouseSidebar />` — tree navigation, file icons par format
- `<WarehouseSettings />` — modal édition `warehouse_path`
- `<DatasetPreview />` — table preview (déjà partiellement existante en B.5)
- `<SidecarEditor />` — formulaire yaml-form pour edit sidecar
- `<FormatBadge />` — petit badge coloré CSV/Parquet/JSON/...

## 4. Backend implémentation

### Module proposé

`src/hmm_studio/server/warehouse.py` :

```python
from pathlib import Path
from typing import Iterator
from datetime import datetime
import yaml
import pandas as pd

FORMAT_READERS = { ... }  # comme ci-dessus

def scan_warehouse(root: Path) -> list[dict]:
    """Recursively scan warehouse dir, return list of dataset entries."""
    entries = []
    for path in root.rglob("*"):
        if path.is_dir() or path.name.endswith(".hmm.yaml"):
            continue
        if path.suffix.lower() not in FORMAT_READERS:
            continue
        entries.append({
            "rel_path": str(path.relative_to(root)),
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime),
            "format": path.suffix.lower().lstrip("."),
            "has_sidecar": (path.parent / f"{path.name}.hmm.yaml").exists(),
        })
    return entries

def load_sidecar(dataset_path: Path) -> dict | None:
    sidecar = dataset_path.parent / f"{dataset_path.name}.hmm.yaml"
    if not sidecar.exists():
        return None
    return yaml.safe_load(sidecar.read_text())

def write_sidecar(dataset_path: Path, meta: dict) -> None:
    sidecar = dataset_path.parent / f"{dataset_path.name}.hmm.yaml"
    sidecar.write_text(yaml.safe_dump(meta, sort_keys=False))

def preview(dataset_path: Path, n: int = 10) -> pd.DataFrame:
    df = FORMAT_READERS[dataset_path.suffix.lower()](dataset_path)
    return df.head(n)
```

### Cache (simple)

Cache in-memory du scan, TTL 5 secondes ou invalidation explicite via
`/refresh`. Pas de Redis ou autre — un dict Python suffit.

## 5. Sécurité

Le warehouse est un répertoire **utilisateur local**, donc :
- Pas d'auth additionnelle nécessaire (local-first, l'utilisateur a déjà
  accès au filesystem)
- **MAIS** : path traversal. L'endpoint `/api/warehouse/{rel_path}/preview`
  doit refuser tout `rel_path` qui sort de `warehouse_path`. Validation
  stricte :

```python
def safe_resolve(warehouse_root: Path, rel_path: str) -> Path:
    full = (warehouse_root / rel_path).resolve()
    if not full.is_relative_to(warehouse_root.resolve()):
        raise ValueError(f"path traversal blocked: {rel_path}")
    return full
```

Sans cette protection : `/api/warehouse/../../../../etc/passwd/preview`
fonctionnerait. À tester explicitement.

## 6. Tests

### Backend (`tests/studio/test_warehouse.py`)

| Test | Vérifie |
|---|---|
| `test_scan_empty_warehouse` | Dir vide → liste vide |
| `test_scan_detects_all_formats` | CSV, parquet, JSON, Excel détectés |
| `test_scan_ignores_unknown_formats` | `.txt`, `.md` ignorés |
| `test_scan_recursive` | Sous-dossiers explorés |
| `test_scan_sidecar_pairing` | `dataset.csv` + `dataset.csv.hmm.yaml` → flag has_sidecar=True |
| `test_preview_csv` | Preview 10 lignes correctes |
| `test_preview_parquet` | Idem parquet |
| `test_preview_excel` | Idem Excel |
| `test_load_sidecar_yaml` | Parse correct |
| `test_write_sidecar_roundtrip` | Write puis read = identité |
| `test_path_traversal_blocked` | `../../../etc/passwd` rejeté avec ValueError |
| `test_upload_appends_to_warehouse` | POST upload crée fichier dans warehouse |

### Frontend (Playwright)

| Test | Vérifie |
|---|---|
| `warehouse_sidebar_displays_files` | Sidebar montre fichiers du warehouse |
| `select_dataset_shows_preview` | Click sur dataset → preview |
| `edit_sidecar_persists` | Edit metadata → reload → metadata persisté |
| `use_for_fit_navigates_to_fit_with_dataset` | Bouton "Use for fit" pré-remplit le fit launcher |

## 7. Définition de "done"

- [x] Module `server/warehouse.py` avec 5 fonctions principales (B.10a)
- [x] 6 nouveaux endpoints REST + promote endpoint avec OpenAPI doc (B.10a + B.10b)
- [x] Composants frontend : sidebar, preview enrichi, sidecar editor (B.10b)
- [x] Path traversal bloqué et testé (B.10a)
- [x] Backend tests (17 total : 15 B.10a + 2 promote B.10b)
- [ ] Frontend E2E for warehouse deferred — needs CI fixture (configured warehouse dir), tracked as B.10c
- [ ] Section README "Data warehouse" avec capture d'écran
- [ ] Settings UI exposée (warehouse_path éditable) — partial: read-only display + copy in sidebar footer (B.10b), full settings page deferred
- [ ] Migration sidecar v1 → v2 documentée d'avance (anticipation)

## 8. Successeurs hors-scope

- **B.10.1** : Versioning git-like (`git init` du warehouse) → reject sauf signal
- **B.10.2** : Remote storage (S3, GCS, Azure Blob) → reject sauf pivot SaaS
- **B.10.3** : Lineage / DAG cross-fits → DVC / MLflow territory, reject
- **B.10.4** : Multi-warehouse / workspaces → reconsider si user a réellement plusieurs projets simultanés
- **B.10.5** : Indexation full-text / search → overkill pour < 100 datasets

## 9. ADR à créer

`docs/decisions/0010-data-warehouse-scope.md` :
- Pourquoi local-only ?
- Pourquoi pas de DB / pas de versioning ?
- Pourquoi sidecar yaml et pas DB metadata ?
- Limites posées pour anti-scope-creep
