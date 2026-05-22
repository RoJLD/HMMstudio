# ADR-0002 : Stack et architecture du sous-projet B (web UI)

**Date** : 2026-05-22
**Status** : Accepted

## Contexte

Le sous-projet B (`hmm-studio` web UI) ajoute une UI graphique au-dessus
de `hmm-core` (sous-projet A, livré). Le spec draft
[`2026-05-21-hmm-studio-web-design.md`](../specs/2026-05-21-hmm-studio-web-design.md)
identifiait 6 décisions structurantes à arbitrer avant l'implémentation.
Cet ADR les acte.

## Décisions

| # | Sujet | Choix | Override du reco draft ? |
|---|---|---|---|
| D-1 | Framework frontend | **React + Vite + Tailwind** | Non (reco) |
| D-2 | Bibliothèque graphe | **React Flow** | Non (reco) |
| D-3 | Backend persistence | **SQLite** (via `sqlmodel`) | **OUI** (draft : in-memory) |
| D-4 | Authentication | **Aucune** (local-only, bind 127.0.0.1) | Non (reco) |
| D-5 | Packaging | **FastAPI sert build React via StaticFiles** (single binary `hmm-studio serve`) | Non (reco) |
| D-6 | Streaming progress Baum-Welch | **Polling 200ms sur `model.monitor_.history` + WebSocket push** | Non (reco) |

## Conséquences

### Positives

- Stack frontend mature, dette technique minimale (React Flow + Tailwind + Vite est un trio bien rodé).
- `pip install hmm-studio[web]` + `hmm-studio serve` = expérience d'install minimale pour l'utilisateur final.
- Persistence SQLite (vs in-memory) signifie que l'historique des fits **survit aux redémarrages du serveur** — utile en pratique pour revenir sur un fit la semaine suivante.
- Pas d'auth = pas de plomberie OAuth/JWT à maintenir. Bind localhost reste sûr par défaut.
- Polling de la `monitor_.history` ne touche pas à `hmmlearn` — pas de version coupling.

### Négatives

- SQLite + sqlmodel ajoute ~150 lignes de boilerplate (schemas + migrations Alembic ou simples `metadata.create_all`).
- Pas d'auth bloque l'usage multi-utilisateur ou exposé public — décision à reprendre dans un ADR séparé si besoin émerge.
- Polling 200ms a une latence perceptible mais acceptable; le coût en CPU est négligeable.
- React + tout son écosystème = bundle frontend de quelques centaines de Ko. Acceptable pour un outil desktop-like.

### Risques

- **Migration de schéma SQLite** : pas d'outil de migration au MVP. Si on ajoute des champs après le ship, l'utilisateur doit `rm hmm_studio.db` (perd l'historique). À reconsidérer si l'outil devient sérieux.
- **Bundle frontend dans la wheel Python** : Vite build doit être run avant `python -m build` pour que les statics soient inclus. Ajouter une étape `pre-build` dans le packaging.

## Détails d'implémentation acquis (vs draft)

### SQLite schema (initial)

3 tables principales :

```
datasets
├── id           uuid PK
├── filename     str
├── n_rows       int
├── n_cols       int
├── dtypes       json
├── created_at   datetime
└── path         str  (filesystem path to uploaded CSV)

fit_jobs
├── id           uuid PK
├── topology     json  (the validated Topology serialized)
├── dataset_id   FK datasets.id
├── seed         int? (override)
├── status       enum (queued, running, done, failed, cancelled)
├── progress     json  (last known monitor_.history)
├── result_path  str?  (filesystem path to model.pkl + summary.json bundle)
├── error        str?
├── started_at   datetime?
├── ended_at     datetime?
└── created_at   datetime

annotations    (deferred, sub-project C)
```

DB file : `~/.hmm-studio/hmm_studio.db` (or override via `HMM_STUDIO_DB_PATH` env var).
Uploads : `~/.hmm-studio/uploads/{dataset_id}.csv`.
Results : `~/.hmm-studio/results/{fit_job_id}/{model.pkl,summary.json,fit_log.txt}`.

### Packaging command

```bash
# Development:
hmm-studio serve --reload --port 8000

# Production:
hmm-studio serve --port 8000 --host 127.0.0.1
```

The CLI is exposed via `[project.scripts] hmm-studio = "hmm_studio.cli:app"` in `pyproject.toml`.

### Threading

Fits run in a `ThreadPoolExecutor` (max_workers = `os.cpu_count() // 2`, configurable). One job per worker. `numpy` releases the GIL during heavy ops so threads are effective.

## Revisit triggers

- Si l'outil passe à un usage multi-utilisateur : reconsidérer D-3 (PostgreSQL) et D-4 (auth).
- Si la latence 200ms du streaming devient gênante : passer à un callback patch d'hmmlearn (D-6).
- Si Vite build se révèle pénible à intégrer dans CI/packaging : envisager un pre-built CDN ou un git submodule pour les statics.

## Pointeurs

- Spec B : [docs/specs/2026-05-21-hmm-studio-web-design.md](../specs/2026-05-21-hmm-studio-web-design.md)
- Plan B.1 (à venir) : [docs/plans/2026-05-22-b1-backend-skeleton.md](../plans/2026-05-22-b1-backend-skeleton.md)
- Roadmap : [docs/roadmap.md](../roadmap.md)
