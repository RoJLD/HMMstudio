# Design — Visualisations avancées + NHMM animé (sub-projet C)

**Date** : 2026-05-21
**Auteur** : Robin Denis (draft auto-écrit par Claude Code, à brainstormer)
**Status** : **DRAFT** — décisions ouvertes non arbitrées. Brainstormer
quand B aura livré (cette spec dépend de l'architecture B). Considère
cette spec comme un point de départ, pas un livrable.

> ⚠ Cette spec a été générée automatiquement pour fixer le périmètre de C
> dans la roadmap. Quand tu reprends C, relance `superpowers:brainstorming`
> avec ce doc + l'expérience d'usage de B comme inputs. Plusieurs choix
> de C dépendent de comment B a été réellement implémenté.

## Contexte

B (web UI MVP) ship avec :
- Topologie statique (matrice A constante)
- Heatmap A apprise (statique)
- Viterbi colorisé sur la timeline
- Émissions par état (statique)
- K-scan en CLI (pas dans l'UI)

C ajoute ce qui fait basculer l'outil dans le "wow factor" — les
fonctionnalités qui différencient du tableau Excel + matplotlib :
- **NHMM "breathing"** : la matrice A se déforme dans le temps quand on
  scrub la timeline
- **Replay temporel** : rejouer la séquence d'observations + états comme
  une animation
- **Comparaison de fits** : K-scan, seed-scan, side-by-side BIC/AIC
- **Export publication-ready** : SVG/PDF haute résolution, palette
  accessible
- **Annotations externes** : importer des dates clés (interventions,
  événements de marché, etc.) overlayés sur la timeline
- **Multi-séquences** : visualiser un fit appris sur plusieurs sessions

## Décisions ouvertes

### D-7 Backend NHMM "breathing"

Refactor du code existant dans le crypto dashboard, OU réécriture native dans `hmm_core` (déjà fait en A.1 si le NHMM core est livré).

**Recommandation** : **A.1 est déjà fait** (NHMM dans hmm_core v0.2.0). C consomme via `from hmm_core import fit_nhmm, NHMMFittedModel`. Pas de refactor à faire.

### D-8 Animation de la heatmap A(t)

| Option | Pour | Contre |
|---|---|---|
| **Interpolation entre snapshots A_t[t]** (reco) | Léger, Plotly fait nativement avec `animation_frame` | Latence de chargement si T > 5000 |
| Animation continue canvas-rendered | Smoother à grand T | Effort d'implémentation x5 |
| Snapshot à la frame courante du slider | Le moins coûteux, pas d'animation | Pas "breathing", juste réactif |

**Recommandation : interpolation Plotly + slider Plotly**. Mockup :
quand tu déplaces le slider du temps, la heatmap A(t) re-render avec le
slice courant. Plotly gère ça nativement.

### D-9 Replay temporel — granularité

| Option | Pour | Contre |
|---|---|---|
| **Frame-by-frame avec play/pause + slider** (reco) | Standard, UX familière | — |
| Auto-replay loop | Mode démo | Distraction; surchargé sur petit écran |
| Step manuel uniquement | Maximum de contrôle | Friction pour exploration rapide |

**Recommandation : frame-by-frame + play/pause + slider**, copier l'ergonomie du dashboard crypto existant.

### D-10 K-scan UI

| Option | Pour | Contre |
|---|---|---|
| **Picker côté frontend + pré-calcul backend en parallèle** (reco) | UI réactive, calcul fait une fois | Coût d'upload : lance K fits |
| Onglets séparés par K avec re-fit à chaque switch | Simple à coder | Lent à utiliser |
| Affichage table BIC/AIC seulement, pas d'inspection détaillée | Minimal | Limite la valeur |

**Recommandation : pré-calcul de la grille de K au moment du Fit ("Fit + scan K=2..7"), puis picker côté frontend pour switcher entre les K sans re-fit**. Backend lance les K fits en parallèle dans le ThreadPoolExecutor, frontend affiche table BIC/AIC + permet de "ouvrir" un K spécifique pour inspection détaillée.

### D-11 Export figures

| Option | Pour | Contre |
|---|---|---|
| **Plotly to_image + download via FastAPI** (reco) | Backend déjà a Plotly via Python | Requires kaleido pour PDF/SVG |
| Frontend html2canvas + jspdf | Pas de dépendance backend | Quality inférieure |
| Server-side Selenium + screenshots | Maximum de fidelité | Complexe à packager |

**Recommandation : Plotly + Kaleido côté backend, endpoint `/api/export/{job_id}/figure/{fig_name}?format=svg|pdf|png&dpi=300`**.

### D-12 Annotations externes

Format d'import (CSV ? JSON ? YAML ?), schéma (date + label + couleur ?), UI (overlay sur timeline avec lignes verticales + labels rotatifs ?).

**Recommandation** :
- Format : CSV avec colonnes `timestamp,label,color?,kind?` (kind = event/range/marker pour différencier les types).
- UI : layer optionnel sur la timeline, toggleable depuis la sidebar.
- Persistence : sauvegardée par job (`annotations.csv` dans `results/{job_id}/`).

### D-13 Multi-séquences

Quand le `fit()` est appelé avec `lengths=[L1, L2, ...]`, comment afficher les résultats ?

**Recommandation** :
- Onglets ou dropdown pour switcher entre séquences.
- Vue "all in one" : timelines empilées avec séparateurs visuels.
- Heatmap A reste globale (apprise sur l'ensemble).

## Découpage en tasks

### C.1 — NHMM breathing UI (A(t) dynamique)

- Backend : endpoint `/api/fit/{job_id}/A_at?t=N` retournant la slice A_t[N]
- Frontend : Plotly heatmap avec `animation_frame` ou re-render sur change du slider t
- Sidebar covariate Z(t) visible : graphique du covariate en parallèle de la matrice
- Tests : visual regression Playwright + smoke

**Effort estimé : ~1 semaine**

### C.2 — Replay temporel

- Frontend : composant TimelinePlayer (play/pause/step/slider, vitesse configurable 1x, 2x, 4x)
- État courant : highlight de la barre Viterbi + position cursor sur tous les sous-graphiques (indicateurs, posterior, A_t)
- Tests : Vitest + interaction

**Effort estimé : ~3-5 jours**

### C.3 — K-scan comparison

- Backend : `/api/fit/start` accepte param `k_range: [2, 3, 4, 5]`, lance K fits en parallèle, retourne `parent_job_id` qui regroupe les K sous-jobs
- WebSocket reporte progress agrégé (k_done / k_total)
- Frontend : page `/results/{parent_job_id}` avec table BIC/AIC, scatter "BIC vs K", picker pour inspection détaillée d'un K
- Tests : pytest + Playwright

**Effort estimé : ~1 semaine**

### C.4 — Export figures

- Backend : `/api/export/{job_id}/figure/{fig_name}?format=svg|pdf|png&dpi=300`
- Figures exportables : transmat heatmap, viterbi timeline, posterior heatmap, emissions per state, A_t at given t
- Dépendance ajoutée : `kaleido` dans `[web]` extras
- Frontend : bouton "Download as SVG/PDF/PNG" sur chaque figure
- Palette CB-friendly (Okabe-Ito ou Wong) en option global settings

**Effort estimé : ~3-5 jours**

### C.5 — Annotations externes

- Backend : `/api/data/{data_id}/annotations/upload` (CSV multipart) + `/api/data/{data_id}/annotations` GET
- Frontend : panel "Annotations" dans la sidebar, drag-drop upload CSV, toggle visibility, edit en place
- Rendering : layer Plotly avec lignes verticales + labels rotatifs
- Persistence : `results/{job_id}/annotations.csv`

**Effort estimé : ~3-5 jours**

### C.6 — Multi-séquences

- Backend : `/api/fit/start` accepte `lengths: [L1, L2, ...]` (mapping vers `hmm_core.fit(lengths=...)`)
- Frontend : si fit multi-séquences, vue Results affiche un dropdown "Sequence 1 / 2 / ..." pour switcher
- Vue alternative "All": timelines empilées
- Tests : pytest sur le mapping + Vitest sur l'UI

**Effort estimé : ~3-5 jours**

**Total MVP C : ~4-6 semaines à temps partiel.**

## Architecture additions

Sur la base de B, C ajoute :

```
src/hmm_studio/server/routes/
├── (existing: topology.py, data.py, fit.py, decode.py)
├── nhmm.py          # /api/fit/{id}/A_at, /api/fit/{id}/covariate
├── export.py        # /api/export/{id}/figure/*
└── annotations.py   # /api/data/{id}/annotations

src/hmm_studio/frontend/src/components/
├── (existing: topology/, data/, fit/, results/)
├── nhmm/            # AtHeatmap, CovariatePanel
├── replay/          # TimelinePlayer
├── compare/         # KscanTable, BicScatter
├── export/          # ExportPanel
└── annotations/     # AnnotationsLayer, AnnotationsUploader
```

## Critères de "done" pour C (MVP)

1. NHMM breathing : un fit avec covariates affiche A_t qui change quand on bouge le slider t.
2. Replay : bouton play déclenche une animation continue de la timeline avec viterbi qui défile.
3. K-scan : choisir K=[2..6] depuis l'UI lance les 5 fits, table BIC/AIC affichée, click → détail du K choisi.
4. Export : bouton "Download as SVG" sur la heatmap A produit un SVG ouvrable dans Illustrator/Inkscape avec couleurs accessibles.
5. Annotations : upload un CSV de 10 événements → overlay visible sur la timeline.
6. Multi-séquences : fit avec lengths=[500, 500, 500] → dropdown UI pour switcher entre les 3 sessions.
7. Coverage backend ≥ 80%.

## Risques techniques

| Risque | Probabilité | Mitigation |
|---|---|---|
| Plotly + Kaleido pesant en image Docker | Moyenne | Imager seulement les builds avec extras `[web]` |
| Animation Plotly lente à T > 10k | Moyenne | Downsample en frontend (1 frame sur N) pour le scrub |
| K-scan parallèle saturé en CPU | Faible | Limiter K parallèles à `os.cpu_count() / 2` |
| Multi-séquences avec hmmlearn surprend (init de séquences distinctes) | Moyenne | Test E2E spécifique multi-séquences avant ship |

## Hors scope C (à reporter post-MVP ou jamais)

- Édition collaborative (multi-utilisateur synchrone) — décision auth+infra
- Mode "diff" entre deux fits — pas demandé
- Mode "Bayesian" (priors Dirichlet sur transitions) — out of hmm-core MVP
- Mode "online learning" (fit incrémental sur stream) — futur
- Mode "ensemble" (moyenne de fits) — pas dans la roadmap

## Étapes pour démarrer C

1. **Attendre que B ship**. Plusieurs choix de C dépendent de comment B a été implémenté (mécanisme de slider, infrastructure WebSocket, etc.).
2. Lance `superpowers:brainstorming` avec ce doc en référence + l'expérience B.
3. Arbitre D-8 à D-13 si encore non tranchées.
4. Crée le plan d'impl via `superpowers:writing-plans`.
5. Exécute via `superpowers:subagent-driven-development`.

## Pointeurs

- Spec B (UI socle) : [docs/specs/2026-05-21-hmm-studio-web-design.md](2026-05-21-hmm-studio-web-design.md)
- A.1 NHMM core (consommé par C.1) : déjà livré dans `hmm_core.nhmm` (v0.2.0)
- Roadmap : [docs/roadmap.md](../roadmap.md)
- Référence visuelle : le dashboard crypto existant ([src/cmex_crypto/viz/hmm_dashboard/](C:\Users\rdenis\VScode\Experiment.Crypto.2026S1.RobinDenis\src\cmex_crypto\viz\hmm_dashboard\)) implémente déjà la plupart de ces features — bonne source d'inspiration UI/UX.
