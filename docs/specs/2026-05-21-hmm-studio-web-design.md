# Design — `hmm-studio` web UI (sub-projet B)

**Date** : 2026-05-21
**Auteur** : Robin Denis (draft auto-écrit par Claude Code, à brainstormer)
**Status** : **DRAFT** — décisions ouvertes non arbitrées. Brainstormer avant
implémentation. Les choix par défaut ci-dessous reflètent la position
recommandée; tu peux les overrider.

> ⚠ Cette spec a été générée automatiquement à partir de la roadmap pour
> éviter qu'elle ne se perde. Elle n'a PAS suivi le cycle brainstorming
> complet. Quand tu reprends B, lance `superpowers:brainstorming` et utilise
> cette spec comme point de départ — pas comme livrable final.

## Contexte

Le sous-projet A (`hmm-core`, livré 2026-05-21) fournit un engine Python +
CLI pour fitter des HMM contraints. B ajoute l'interface graphique : un
éditeur node-based de topologie, l'upload de données, le lancement de fits
en direct avec progression, et la visualisation des résultats.

C'est le morceau "Configurateur" promis dans le framing initial Gemini :
l'utilisateur dessine les états et les transitions au lieu d'écrire des
matrices, et voit le modèle s'animer.

## Décisions ouvertes à arbitrer (6 forks majeurs)

Liste exhaustive des choix qui doivent être tranchés avant d'écrire le
plan d'implémentation B. Les recommandations sont indicatives.

### D-1 Framework frontend

| Option | Pour | Contre |
|---|---|---|
| **React + Vite + Tailwind** (reco) | Écosystème graphes mature (React Flow), Tailwind productif, hot reload Vite excellent | Bundle plus lourd qu'un setup minimaliste |
| Vue 3 + Vite + Tailwind | Plus simple à apprendre si tu n'as jamais touché React | Moins de bibliothèques node-graph natives |
| Svelte/SvelteKit | Compilation efficace, moins de boilerplate | Écosystème node-editor naissant |
| HTMX + Jinja | Backend FastAPI sert le HTML, pas de SPA | L'éditeur node-based va devoir réinventer beaucoup |

**Recommandation : React + Vite + Tailwind**. C'est le seul choix qui te
donne accès à React Flow (voir D-2) sans porter du code soi-même.

### D-2 Bibliothèque graphe / node editor

| Option | Pour | Contre |
|---|---|---|
| **React Flow** (reco) | Custom nodes, drag-drop, edge routing built-in. Très ergonomique. | Quelques limites de styling avancé |
| Cytoscape.js | Très puissant pour analyse de graphes (centralité, etc.) | Moins ergonomique pour l'authoring |
| D3.js custom | Total contrôle | Coût d'écriture x10 |
| react-flow (alternative ?) | Idem ci-dessus | (Identique) |

**Recommandation : React Flow** ([reactflow.dev](https://reactflow.dev/)).
Bibliothèque mature, license MIT, custom nodes natifs (essentiel pour
afficher les paramètres d'émission par état).

### D-3 Backend persistence

| Option | Pour | Contre |
|---|---|---|
| **In-memory dict + filesystem** (reco) | Zero infrastructure, suffit pour usage local | Pas de multi-session, redémarre = perdre l'état |
| SQLite | Persistence simple, single-file DB | Boilerplate ORM |
| PostgreSQL | Robuste, prêt pour multi-utilisateur | Overkill pour MVP local |
| Redis (cache jobs) | Streaming fit nativement | Une dépendance externe en plus |

**Recommandation : in-memory dict pour les jobs en cours +
filesystem (`./results/`) pour les fits sauvegardés**. Cohérent avec l'usage
local-first; multi-utilisateur sera une décision séparée si jamais.

### D-4 Auth

| Option | Pour | Contre |
|---|---|---|
| **Aucune (local-only)** (reco) | Zero friction, l'outil n'écoute que sur localhost | Pas utilisable derrière un domaine public |
| Basic auth (env vars) | Trivial à activer | Pas vraiment sécurisé |
| OAuth GitHub | Standard si déploiement cloud | Beaucoup de plomberie pour zéro besoin actuel |

**Recommandation : aucune auth au MVP**. Le serveur bind sur 127.0.0.1
par défaut. Si tu veux publier en mode "hosted", auth devient une décision
post-MVP dans un sous-projet séparé.

### D-5 Packaging / distribution

| Option | Pour | Contre |
|---|---|---|
| **FastAPI sert le build React (single binary)** (reco) | Une commande d'install et de run | Couplage build frontend ↔ release backend |
| Docker compose (frontend + backend séparés) | Plus propre architecturalement | Plus lourd à déployer pour un utilisateur final |
| Deux services séparés (npm run + python -m) | Dev-friendly | Mauvaise UX utilisateur final |

**Recommandation : FastAPI sert les static files React via `StaticFiles`,
distribué via `pip install hmm-studio[web]` + `hmm-studio serve`**. L'utilisateur
final fait `pip install hmm-studio[web]` et tape `hmm-studio serve` — c'est tout.

### D-6 Mécanisme de streaming pour la progression de fit

C'est le seul vrai point dur technique. `hmmlearn` ne fournit pas de
callback de progression natif. Options :

| Option | Pour | Contre |
|---|---|---|
| **Polling toutes les 200ms sur `model.monitor_.history`** (reco) | Pas de modification d'hmmlearn, simple à implémenter | Latence ~200ms entre itération et affichage |
| Patcher `hmmlearn` avec un callback custom | Latence quasi-nulle | Couple hmm-studio à une version précise d'hmmlearn |
| Lancer le fit en subprocess avec stdout streaming | Découplé | Overhead I/O + sérialisation du modèle final |

**Recommandation : polling `monitor_.history` toutes les 200ms via une
WebSocket**. C'est largement suffisant — Baum-Welch fait typiquement
10-100 itérations en quelques secondes; 200ms de granularité est
imperceptible côté UX.

---

## Architecture proposée (avec les recos)

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (React + Vite + Tailwind, served by FastAPI)           │
│                                                                  │
│ ┌──────────────────┐  ┌──────────────────┐ ┌─────────────────┐ │
│ │ Topology Editor  │  │ Data Panel       │ │ Results View    │ │
│ │ (React Flow)     │  │ (CSV uploader,   │ │ (heatmap, viterbi│ │
│ │  - drag states   │  │  preview, schema │ │  on graph,       │ │
│ │  - draw edges    │  │  detection)      │ │  emissions,      │ │
│ │  - emission UI   │  │                  │ │  comparison)    │ │
│ └────────┬─────────┘  └────────┬─────────┘ └────────┬────────┘ │
│          │                     │                    │           │
│          └─────────────────────┼────────────────────┘           │
│                                │ Fit Launcher (sidebar)         │
│                                │ + progress streaming           │
└────────────────────────────────┼────────────────────────────────┘
                                 │
              REST + WebSocket   │  (same-origin, CORS-free)
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ Backend (FastAPI + uvicorn)                                      │
│                                                                  │
│ /                       GET   serve index.html                  │
│ /assets/*               GET   serve static (Vite build output)  │
│                                                                  │
│ /api/topology/validate  POST  yaml/json → ok | TopologyError    │
│ /api/data/upload        POST  multipart → data_id + preview     │
│ /api/data/{id}/preview  GET   first N rows + stats              │
│                                                                  │
│ /api/fit/start          POST  {topology, data_id, seed?}        │
│                               → {job_id, status: "running"}     │
│ /ws/fit/{job_id}        WS    streams {iter, log_lik} per       │
│                               iteration; closes on done/error   │
│ /api/fit/{job_id}        GET   {status, log_lik, bic, paths}    │
│ /api/fit/{job_id}/cancel POST cancels the running job           │
│                                                                  │
│ /api/decode             POST  {model_path, data_id}             │
│                               → viterbi + posterior (or path)   │
│                                                                  │
│ Background job runner: ThreadPoolExecutor (CPU-bound fits).     │
│ Job state: in-memory dict keyed by uuid4.                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ Python API
                         ▼
       ┌────────────────────────────────────┐
       │ hmm_core (sub-project A) v0.2.0+   │
       │   Topology, fit, fit_nhmm,         │
       │   load_model, save_model           │
       └────────────────────────────────────┘
```

## Layout repo

Sous `Tools/hmm_studio/src/hmm_studio/` (frère de `hmm_core/`) :

```
src/hmm_studio/
├── __init__.py
├── server/
│   ├── __init__.py
│   ├── app.py                 # FastAPI app + lifespan
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── topology.py        # /api/topology/*
│   │   ├── data.py            # /api/data/*
│   │   ├── fit.py             # /api/fit/* + /ws/fit/*
│   │   └── decode.py          # /api/decode
│   ├── jobs.py                # in-memory job runner + ThreadPoolExecutor
│   ├── schemas.py             # Pydantic models for request/response
│   └── static/                # frontend build output (generated, gitignored)
├── frontend/                  # React source
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/               # fetch wrappers for /api/*
│       ├── components/
│       │   ├── topology/      # React Flow editor + custom nodes
│       │   ├── data/          # uploader + preview
│       │   ├── fit/           # launcher + progress monitor
│       │   └── results/       # heatmap, viterbi, emissions
│       ├── hooks/             # custom React hooks (useWebSocket, etc.)
│       └── lib/               # YAML serializer, validation, etc.
└── cli.py                     # `hmm-studio serve [--port 8000]`
```

`Tools/hmm_studio/pyproject.toml` gains a `[project.optional-dependencies] web = ["fastapi", "uvicorn[standard]", "python-multipart"]` and a new entry point `hmm-studio = "hmm_studio.cli:app"`.

## Découpage en tasks (à raffiner pendant brainstorm)

### B.1 — Backend FastAPI : skeleton + endpoints REST

- FastAPI app skeleton avec lifespan, routing, CORS (localhost-only)
- Pydantic schemas pour topology / fit job / data preview
- `/api/topology/validate` : appelle `Topology.from_yaml + validate()`
- `/api/data/upload` : multipart, stocke en mémoire (limite 50 MB)
- `/api/data/{id}/preview` : retourne head + colonnes + dtypes
- `/api/fit/start` : crée un job_id, lance dans ThreadPoolExecutor, retourne immédiatement
- `/api/fit/{id}` : retourne status
- `/api/fit/{id}/cancel` : annule (en pratique : set a flag, hmmlearn ne supporte pas l'interruption, donc le job peut tourner jusqu'à la fin de l'itération en cours)
- Tests : pytest + httpx AsyncClient

**Effort estimé : ~1 semaine**

### B.2 — WebSocket pour streaming progress

- `/ws/fit/{job_id}` : push toutes les 200ms le contenu de `model.monitor_.history`
- Frontend : `useWebSocket` hook, met à jour un store
- Tests : pytest-asyncio + httpx-ws

**Effort estimé : ~3 jours**

### B.3 — Frontend skeleton (Vite + React + Tailwind + Router)

- Setup Vite + TypeScript + Tailwind
- Router (React Router) : pages `/`, `/fit/:id`, `/results/:id`
- Layout : sidebar + main pane
- Stores : Zustand pour state global (topology en cours, fit en cours)
- Test : Vitest + React Testing Library, smoke test sur App.tsx

**Effort estimé : ~3 jours**

### B.4 — Topology editor avec React Flow

- Custom node "State" : nom, type d'émission (display only — défini globalement), édit-en-place du label
- Custom edge "Transition" : affichage simple, créé par drag node-to-node
- Side panel : `EmissionSpec` configuration globale + `InitSpec` + `FitSpec`
- Export YAML : sérialise le graphe en `Topology` YAML conforme à `hmm-core`
- Import YAML : utilise `/api/topology/validate` + reconstruit le graphe
- Validation live : appelle `/api/topology/validate` à chaque changement, affiche errors
- Tests : Vitest + Testing Library + manual E2E playthrough

**Effort estimé : ~2 semaines**

### B.5 — Data upload + preview + validation CSV

- Component drag-drop upload (max 50 MB)
- Preview : 10 premières lignes, colonnes + dtypes
- Validation cross-référencée avec la topologie courante : vérifier shape (n_features pour Gaussian/GMM/Poisson, single int column pour Multinomial)
- Affichage warnings si mismatch (e.g. "votre topologie attend 2 colonnes, le CSV en a 3")
- Tests : Vitest + Testing Library

**Effort estimé : ~3-5 jours**

### B.6 — Fit launcher + results view

**Fit launcher (panel)** :
- Bouton "Fit" enabled quand topology + data sont valides
- Affiche log-likelihood curve en temps réel (Recharts ou un canvas custom)
- Bouton "Cancel"
- Quand terminé : redirige vers `/results/:id`

**Results view** :
- Heatmap matrice A apprise (avec edges interdits en gris) — using Plotly.js ou react-plotly
- Graphe topologie avec opacity sur edges = probas apprises (réutilise React Flow en mode read-only)
- Bande Viterbi colorisée sur la timeline (timeseries Plotly)
- Posterior P(state | obs ≤ t) : heatmap T×K
- Statistiques d'émission par état (means, covars pour Gaussian)
- Export bouton : "Download model.pkl" + "Download summary.json"

**Effort estimé : ~1-2 semaines**

### B.7 — CLI launcher

`src/hmm_studio/cli.py` :
- Typer command `hmm-studio serve [--port 8000] [--host 127.0.0.1]`
- Lance uvicorn avec l'app FastAPI

**Effort estimé : 1 jour**

### B.8 — Packaging + docs utilisateur

- `pyproject.toml` : ajouter `[project.optional-dependencies].web`, entry point
- Vite build → static dans `src/hmm_studio/server/static/` (gitignored, généré au build)
- Mise à jour README : section "Web UI" avec install + screenshots
- Test E2E Playwright : install propre + golden path (dessiner graphe → upload CSV → fit → résultats)

**Effort estimé : ~3-5 jours**

**Total MVP B : ~6-8 semaines à temps partiel.**

## Hors scope MVP B (à reporter en C ou post-MVP)

- NHMM "breathing" matrices (animation continue) → C.1
- Replay temporel (timeline scrubber) → C.2
- K-scan comparison side-by-side → C.3
- Export figures publication-ready → C.4
- Annotations événements externes (marquage de dates clés) → C.5
- Multi-séquences UI → C.6
- Authentification → post-MVP si besoin
- Multi-utilisateur → post-MVP si besoin
- Sauvegarde cloud → post-MVP si besoin

## Risques techniques

| Risque | Probabilité | Mitigation |
|---|---|---|
| React Flow performance à K > 20 états | Moyenne | Limiter visuellement à K ≤ 12 dans le MVP, message clair au-delà |
| Fit longs bloquent l'event loop FastAPI | Élevée | `ThreadPoolExecutor` + `async def` endpoints (numpy release le GIL pendant les calculs lourds) |
| WebSocket `model.monitor_.history` n'a pas l'attendu | Moyenne | Vérifier sur hmmlearn 0.3.x avant B.2; fallback : polling REST si non disponible |
| CSV très gros (>50 MB) | Faible | Refus explicite au upload, message clair |
| Build frontend cassé entre sessions dev (npm install vs npm ci, etc.) | Moyenne | Pinner versions exactes dans `package-lock.json`, CI Z.1 doit aussi tester le build |

## Critères de "done" pour B (MVP)

1. `pip install -e ".[web,dev]"` réussit dans un venv neuf.
2. `npm install && npm run build` dans `src/hmm_studio/frontend/` réussit.
3. `hmm-studio serve` ouvre `http://127.0.0.1:8000` avec l'éditeur visible.
4. Un utilisateur peut : dessiner un graphe à 3 états, upload `examples/data_gaussian.csv` (existant), cliquer "Fit", voir la barre de progression se remplir, et obtenir un résultat avec le Viterbi colorisé.
5. Le YAML produit par l'éditeur (export) est byte-compatible avec `hmm-fit run` (CLI de A).
6. Test E2E Playwright passe le golden path.
7. Coverage backend ≥ 80%, coverage frontend ≥ 60% (frontend tests sont historiquement plus coûteux à maintenir).
8. ADR-0002 documentant les 6 décisions arbitrées (stack frontend, persistence, etc.).

## Pointeurs

- Sous-projet A (consommé) : [docs/specs/2026-05-21-hmm-core-design.md](2026-05-21-hmm-core-design.md)
- Roadmap : [docs/roadmap.md](../roadmap.md)
- ADR-0001 (backend hmmlearn) : [docs/decisions/0001-backend-hmmlearn-patch.md](../decisions/0001-backend-hmmlearn-patch.md)
- Sous-projet C (visualisations avancées qui dépendront de B) : [docs/specs/2026-05-21-hmm-viz-advanced-design.md](2026-05-21-hmm-viz-advanced-design.md)
- React Flow : [reactflow.dev](https://reactflow.dev/) — référence de la bibliothèque graphe recommandée

## Étapes pour démarrer B

1. Lance `superpowers:brainstorming` avec ce doc en référence.
2. Arbitre les 6 décisions ouvertes (D-1 à D-6). Écris un ADR-0002 dans `docs/decisions/`.
3. Crée le plan d'implémentation via `superpowers:writing-plans`. Découpe en B.1 → B.8 (chaque sous-task ~3 jours à 2 semaines).
4. Exécute via `superpowers:subagent-driven-development`.
5. Met à jour la roadmap quand B livre.
