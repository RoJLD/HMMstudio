# `hmm-studio` — Roadmap complète

**Date de création** : 2026-05-21
**Auteur** : Robin Denis
**Dernière mise à jour** : 2026-05-22 (session "fais toutes les phases")

> Document vivant. À ré-éditer à chaque transition de phase (fin de
> sous-projet, décision majeure, pivot). Ce n'est pas un spec — c'est la
> carte stratégique au-dessus des specs. Les specs détaillés et les plans
> d'implémentation par sous-projet vivent dans `docs/specs/` et
> `docs/plans/`.

---

## Vision

`hmm-studio` est un outil unifié pour **configurer, entraîner et
visualiser des HMM contraints**, agnostique du domaine d'application.
La promesse :

- L'utilisateur dessine la topologie (états + transitions autorisées) dans
  une UI graphique au lieu d'écrire à la main une matrice K×K.
- Il pointe vers ses données (CSV/JSON).
- L'outil entraîne via Baum-Welch contraint, montre la convergence en
  direct, et affiche le résultat (chemin Viterbi colorisé sur le graphe,
  heatmaps, statistiques d'émission).
- Les fits sont reproductibles, exportables, et inspectables par d'autres
  outils (parquet, JSON, pickle).

Le projet est découpé en **4 sous-projets** indépendants mais chaînés.
Chaque sous-projet est livrable seul et apporte une fonctionnalité
distincte à l'utilisateur.

---

## Vue d'ensemble — où on en est

```
Phase    Sous-projet                       Statut         Dépend de   Échéance estimée
─────────────────────────────────────────────────────────────────────────────────────────
   A     hmm-core (Python engine + CLI)    SHIPPED v0.1   —           livré 2026-05-21
   A.next Polish (GMM tied bug, coverage,  SHIPPED        A           livré 2026-05-22
         lengths param)
   A.1   NHMM dans le core (fit_nhmm)      SHIPPED v0.2   A           livré 2026-05-22
   D     Migration dashboard crypto        VALIDATED      A           regression test
                                           (regression               passe, ADR ajoutée
                                           + ADR, pas               dans crypto repo,
                                           swap)                     non commitée
   Z.1   GitHub Actions CI + pre-commit    SHIPPED        —           livré 2026-05-22
   B     hmm-studio web UI                 SPEC DRAFTED   A, A.1      ~6-8 semaines
                                                                     spec à brainstormer
   C     Visualisations avancées + viz NHMM SPEC DRAFTED  B           ~4-6 semaines
                                                                     spec à brainstormer
   Z.2+  Doc site, release, packaging      NOT STARTED    B, C        continu
```

### Graphe de dépendances

```
                       ┌────────────┐
                       │  A: core   │ ✓ DONE
                       └─────┬──────┘
                             │
              ┌──────────────┼────────────┐
              ▼              ▼            ▼
         ┌────────┐    ┌────────────┐  ┌─────────────┐
         │ D: mig │    │ B: studio  │  │ A.next:     │
         │ crypto │    │ (web UI)   │  │ NHMM core   │
         └────────┘    └─────┬──────┘  └──────┬──────┘
                             │                │
                             └──────┬─────────┘
                                    ▼
                             ┌─────────────┐
                             │ C: viz adv  │
                             └─────────────┘
```

A débloque B et D en parallèle. C dépend de B (UI) et d'une extension
NHMM dans `hmm-core` (qu'on peut faire en A.next ou comme prélude à C).

---

## Phase A — `hmm-core` (livré)

**Status** : SHIPPED · `Tools/hmm_studio/docs/specs/2026-05-21-hmm-core-design.md` · 54 tests, 87% coverage

### Ce qui ship

- Engine Python pur : `Topology`, `fit()`, 4 sous-classes contraintes
  (Gaussian/GMM/Multinomial/Poisson), 4 stratégies d'init.
- Format YAML pour les topologies + IO complet (load/save modèle, summary
  JSON, parquet décodé).
- CLI `hmm-fit validate / run / decode / show`.
- Test E2E sur exemple 4-états left-right.
- ADR-0001 documentant le choix backend.

### Dette identifiée (à traiter dans A.next ou en cours de B)

| Item | Priorité | Notes |
|---|---|---|
| `_n_params` GMM `tied` over-counts | Importante | Fixer avant que B expose un sélecteur de covariance avec BIC |
| Coverage gap sur `init.py` (74%) — branches multinomial-kmeans + covariances non-`full` | Moyenne | Ajouter 3-4 tests paramétrés |
| `data_frequencies` ne gère pas multi-séquences (`lengths`) | Moyenne | Bloquant si A est utilisé sur des datasets concaténés |
| `_apply_mask` warning emission stacklevel sur fallback | Faible | Cosmétique |
| Validation `ValueError` non traduite en `TopologyError` quand un cast int/float YAML échoue | Faible | Edge case |

### A.next (extensions optionnelles)

À planifier comme mini-sous-projets séparés, chacun ~1-2 jours :

- **A.1** : NHMM (transitions covariate-dependent) — actuellement dans le
  dashboard crypto via une approche 2-étapes (logistic regression sur les
  transitions). À promouvoir dans `hmm-core` pour que B puisse l'animer.
  Prérequis de **C**.
- **A.2** : Support multi-séquences via `lengths` dans `fit()` et `init.*`.
- **A.3** : Pin `hmmlearn>=0.4` quand sortie (re-tester les 4 sous-classes
  contraintes).
- **A.4** : Coverage gap fixes (multinomial-kmeans path + covariances
  non-full).

---

## Phase B — `hmm-studio` web UI

**Status** : NOT STARTED · besoin brainstorm/spec/plan séparé
**Dépend de** : A (impératif), A.1 NHMM (souhaitable mais pas bloquant)

### Vision

L'éditeur node-based promis dans la framing initiale "Gemini". L'utilisateur :

1. Ouvre une page web.
2. Glisse-dépose des nœuds (états) sur un canvas, tire des arêtes entre
   eux (transitions autorisées).
3. Configure le type d'émission, les hyperparams de fit, dans un panneau
   latéral.
4. Upload un CSV.
5. Clique "Fit" — une barre de progression montre Baum-Welch converger en
   live (log-vraisemblance qui monte), avec annulation possible.
6. Le résultat s'affiche : chemin Viterbi colorisé sur le graphe original,
   heatmap de la matrice A apprise, statistiques d'émission par état.

### Architecture proposée

```
┌──────────────────────────────────────────────────┐
│ Frontend (React + React Flow + Tailwind)         │
│ ┌──────────────┐  ┌────────────┐  ┌────────────┐ │
│ │ Topo Editor  │  │ Data Panel │  │ Results    │ │
│ │ (React Flow) │  │ (CSV up)   │  │ (heatmap,  │ │
│ │              │  │            │  │  viterbi)  │ │
│ └──────────────┘  └────────────┘  └────────────┘ │
└──────────────────┬───────────────────────────────┘
                   │ REST + WebSocket
                   ▼
┌──────────────────────────────────────────────────┐
│ Backend (FastAPI)                                │
│                                                  │
│ /api/topology/validate  POST yaml/json -> ok|err │
│ /api/fit/start          POST topo+data -> job_id │
│ /ws/fit/{job_id}        stream log-lik per iter  │
│ /api/fit/{job_id}/result GET     -> FittedModel  │
│ /api/decode             POST model+data -> path  │
└──────────────────┬───────────────────────────────┘
                   │ Python API
                   ▼
       ┌────────────────────────────┐
       │ hmm_core (sub-project A)   │
       └────────────────────────────┘
```

### Décomposition (sous-modules à brainstormer)

| ID | Module | Effort | Dépend |
|---|---|---|---|
| **B.1** | Backend FastAPI : endpoints REST + persistence des jobs en mémoire | ~1 sem | A |
| **B.2** | Frontend skeleton : Vite + React + Tailwind + routing + layout | ~3 j | — |
| **B.3** | Topology editor node-based (React Flow) + export YAML | ~2 sem | B.1, B.2 |
| **B.4** | Data upload + preview + validation CSV/JSON | ~3-5 j | B.1, B.2 |
| **B.5** | Fit launcher + progress streaming (WebSocket) + monitor UI | ~1 sem | B.1, B.3 |
| **B.6** | Results view : heatmap A, viterbi sur graphe, gaussiennes émission, comparaison K-scan | ~1-2 sem | B.5 |

**Total estimé** : 6-8 semaines à temps partiel, en série. Possible parallélisation B.1 ↔ B.2.

### Décisions clés à prendre AVANT le spec B

1. **Stack frontend** : React Flow (référence) vs Cytoscape.js vs custom
   D3. React Flow gagne sur l'ergonomie node-based; Cytoscape gagne sur
   l'analyse de graphes (mais on n'en a pas besoin ici).
2. **Persistence backend** : in-memory only (recommandé pour MVP) vs
   SQLite vs Postgres. MVP n'a pas besoin de multi-utilisateur.
3. **Auth** : none (local-only) vs basic vs OAuth. Recommandation : none
   pour MVP, l'outil est local-first.
4. **Packaging** : Docker compose unique vs deux services séparés vs
   tout-en-un (FastAPI sert aussi les static frontend). Recommandation :
   tout-en-un pour MVP — FastAPI sert le build React via `StaticFiles`.
5. **Streaming Baum-Welch** : nécessite hook dans `hmmlearn`'s
   `monitor_.history`. Soit on attend le fit complet, soit on patch
   `hmmlearn` pour exposer un callback. **Décision technique non
   triviale**. Solution intermédiaire : poller toutes les ~200ms et lire
   `model.monitor_.history`.
6. **NHMM dans l'éditeur** : juste topologie statique en MVP B, ou
   covariate-dependent transitions (animation "breathing") dès le
   départ ? Recommandation : statique en B, animation en C.

### Risques techniques

| Risque | Mitigation |
|---|---|
| `hmmlearn` ne fournit pas de callback de progression | Polling `monitor_.history` toutes les 200ms suffit pour la fluidité perçue |
| React Flow custom-node performance à K > 20 états | Limiter visuellement à K ≤ 12 dans le MVP; au-delà, switch à une vue tabulaire |
| Long fits bloquent l'event loop FastAPI | Lancer `fit()` dans un `ThreadPoolExecutor` (CPU-bound mais GIL release-friendly via numpy) |
| CSV upload de gros datasets (>100 MB) | Limiter à 50 MB en MVP avec message clair; streaming upload en post-MVP |

### Définition de "done" pour B (MVP)

- Un utilisateur installe le studio (`docker compose up` ou `pip install hmm-studio[web] && hmm-studio serve`), ouvre `http://localhost:8000`, dessine un graphe à 3 états, upload un CSV gaussien, lance un fit, voit la barre de progression, et obtient un résultat avec le Viterbi colorisé. Aucune connaissance Python requise.
- Le YAML produit par l'éditeur est byte-compatible avec ce que `hmm-fit` (CLI de A) accepte.
- Test E2E Playwright/Cypress couvre le golden path.

---

## Phase C — Visualisations avancées + NHMM animé

**Status** : NOT STARTED
**Dépend de** : B (UI socle), A.1 (NHMM dans core)

### Périmètre

C'est le polish "wow factor". Pas indispensable au MVP mais c'est ce qui
différencie l'outil d'un Jupyter-notebook-amélioré.

| ID | Feature | Effort | Description |
|---|---|---|---|
| **C.1** | NHMM "breathing" — la matrice A se déforme avec le temps | ~1 sem | Animation continue de la heatmap A au-dessus de la timeline; trace le flux des transitions covariate-dependent |
| **C.2** | Replay temporel | ~3-5 j | Slider qui rejoue la séquence d'observations + état Viterbi étape par étape, comme un timelapse |
| **C.3** | Comparaison de fits (K-scan, seed-scan) | ~1 sem | Side-by-side BIC/AIC pour plusieurs K, plusieurs seeds — picker UI |
| **C.4** | Export figures publication-ready | ~3-5 j | SVG / PDF / PNG haute résolution; choix palette accessible (CB-friendly) |
| **C.5** | Annotations & événements externes | ~3-5 j | Importer des dates clés (CSV) pour les overlayer sur la timeline (similaire à l'existant dans le dashboard crypto) |
| **C.6** | Multi-séquences | ~3-5 j | Fit sur un dataset de plusieurs sessions (avec `lengths`); UI pour visualiser un fit par session |

**Total estimé** : 4-6 semaines à temps partiel.

### Décisions clés à prendre AVANT le spec C

1. **NHMM "breathing"** : refactor du code crypto-dashboard existant
   (déjà fonctionnel) vs réécriture dans `hmm-core`. Recommandation :
   promouvoir dans core (A.1) puis consommer depuis B.
2. **Format d'animation** : interpolation entre snapshots de A (cheap)
   vs animation continue (canvas-rendered, plus joli). Recommandation :
   interpolation pour MVP.
3. **Backend pour C.3 (comparaison)** : refit live à chaque changement de
   K vs pré-calcul d'une grille de K. Le second est plus rapide pour
   l'utilisateur, plus coûteux à l'upload.

---

## Phase D — Migration du dashboard crypto

**Status** : NOT STARTED
**Dépend de** : A (stable; aujourd'hui c'est OK)

### Périmètre

Le dashboard HMM existant dans `Experiment.Crypto.2026S1.RobinDenis/src/cmex_crypto/viz/hmm_dashboard/` utilise sa propre logique de fit (`model.py:fit_hmm`). Il pourrait consommer `hmm-core` à la place, ce qui :

- Élimine la duplication de logique.
- Bénéficie immédiatement des contraintes structurelles (si tu veux un
  modèle left-right pour BTC, c'est gratuit).
- Centralise les bugs/améliorations dans un seul endroit.

### Étapes

1. Ajouter `hmm-studio` comme dépendance dev de `Experiment.Crypto`
   (`pip install -e ../../Tools/hmm_studio`).
2. Remplacer `cmex_crypto.viz.hmm_dashboard.model.fit_hmm` par un appel à
   `hmm_core.fit.fit()` avec une `Topology` construite à la volée
   (ergodique, gaussian, etc.) — wrapper de compatibilité.
3. Vérifier que les outputs (transmat, viterbi, posterior, BIC) sont
   numériquement identiques à 1e-10 — tests de régression.
4. Quand stable, supprimer le code mort dans `cmex_crypto.viz.hmm_dashboard.model`.
5. Mettre à jour le `notes/decisions.md` du projet crypto avec une ADR.

### Effort estimé

~1-2 semaines à temps partiel. C'est principalement du wiring + tests de
régression. La logique étant équivalente, pas de gros risque.

### Décision-clé

À faire **avant** ou **après** B ?

- **Avant B** : valide que `hmm-core` est utilisable par un vrai consommateur
  (le dashboard crypto), durcit l'API. Pas besoin de la web UI pour ça.
- **Après B** : on a déjà eu un autre consommateur (B) qui aura forcé les
  durcissements; le dashboard crypto bénéficie d'une core plus mature.

**Recommandation** : faire D **avant** B. Une migration interne est
moins risquée qu'un MVP visible, et elle nous donne un deuxième usage de
`hmm-core` qui fera émerger les vrais problèmes d'API (notamment NHMM
qui est déjà dans le dashboard).

---

## Phase Z — Continu / cross-cutting

Pas un sous-projet en soi, mais des concerns à entretenir tout du long :

### Z.1 CI/CD

Aujourd'hui : aucune CI. Le repo est local-only, pas de remote.

À ajouter quand on push sur un remote (GitHub) :
- GitHub Actions : `pytest` + `ruff` + `black --check` sur push/PR.
- Matrix Python 3.11 / 3.12 / 3.13.
- Coverage badge.
- Pre-commit hooks (déjà configurables via `ruff` et `black` dans `pyproject.toml`).

### Z.2 Documentation

Aujourd'hui : `README.md`, ADR-0001, spec, plan. C'est largement suffisant pour A.

Quand B ship :
- Docs site (mkdocs-material) — quickstart user-facing, screenshots, video démo.
- API reference auto-générée (sphinx ou pdoc).
- Architecture doc (diagrammes Mermaid).

### Z.3 Release / packaging

Aujourd'hui : install local seulement (`pip install -e ...`).

Targets :
- **v0.1.0** (atteint) : A livré, install local.
- **v0.2.0** : D fini (dashboard crypto migré).
- **v0.5.0** : B MVP livré.
- **v0.9.0** : C livré.
- **v1.0.0** : public PyPI release. ADR pour la décision (vendre ou
  donner). Choix de licence définitif.

### Z.4 Sécurité

Si B passe en multi-utilisateur ou exposé sur réseau :
- Auth (a minima basic auth ou OAuth GitHub).
- Validation stricte des uploads (CSV size, types, injection).
- Sandboxing du fit (jamais d'exécution de code utilisateur).
- Audit log des fits.

Pas nécessaire en MVP local-only.

---

## Planning indicatif

Hypothèse : ~10-15h/semaine sur ce projet. Toutes les durées sont des
estimations larges; à corriger après chaque phase.

```
Semaine     Sous-projet     Livrable
─────────────────────────────────────────────────────────────
S+0         A               ✓ SHIPPED 2026-05-21
S+1         D + A.1         Migration dashboard crypto + NHMM dans core
S+3         A.next polish   Coverage gap fixes, GMM tied bug, lengths param
S+4..S+11   B               Studio web MVP (8 semaines)
S+12        Z (docs)        Quickstart + screenshots
S+13..S+18  C               Animations + comparaisons + export
S+19        Z (release)     v1.0 PyPI, decision licence
```

### Jalons (milestones)

- **M1** : `hmm-core` v0.1 livré (✓ atteint)
- **M2** : Dashboard crypto migré, NHMM dans core. `hmm-core` v0.2.
- **M3** : Studio MVP utilisable par un utilisateur sans connaissance Python.
- **M4** : Visualisations avancées + tous les exemples publication-ready.
- **M5** : v1.0 PyPI public.

---

## Décisions ouvertes à arbitrer

Liste des choix qui ne sont pas tranchés. À résoudre quand on commence la
phase concernée (pas avant — risque de pré-décider sans le contexte).

1. **Migration dashboard crypto avant ou après B ?** (recommandation : avant — voir phase D)
2. **Stack frontend de B** : React Flow vs Cytoscape (recommandation : React Flow)
3. **Backend persistence de B** : in-memory vs SQLite (recommandation : in-memory MVP)
4. **NHMM "breathing" en B ou en C ?** (recommandation : statique en B, animé en C)
5. **PyPI public ou private ?** — à décider en M5.
6. **Licence finale** : MIT (par défaut) vs Apache-2 (patent grant) vs
   proprio. Aucun choix encore pris.
7. **Doc site** : mkdocs vs docusaurus vs custom. À trancher en Z.2.

---

## Indicateurs de santé du projet

À monitorer en continu :

| Métrique | Cible | 2026-05-21 | 2026-05-22 |
|---|---|---|---|
| Test coverage `src/hmm_core/` | ≥ 85% | 87% | 92% ↑ |
| Test count | croissant | 54 | 66 ↑ |
| Tests passing | 100% | 100% | 100% ✓ |
| Open dette (items du final review) | ≤ 5 | 3 | 0 ✓ |
| Sub-projects livrés / planifiés | — | 1 / 4 | 2 + 1 validé / 5 |
| Specs draftées (B, C) | — | 0 | 2 ✓ |
| CI configurée | oui | non | oui (en attente de remote) |

---

## Comment utiliser ce document

- **Avant de commencer une phase** : lis le spec correspondant (`docs/specs/`),
  pas seulement cette roadmap.
- **Pendant** : ne modifie pas cette roadmap; modifie le spec / plan / journal.
- **À la fin d'une phase** : met à jour la table "Vue d'ensemble" et ajoute une
  ADR si une décision majeure a été prise (e.g. choix de stack pour B).
- **Tous les 3 mois** : relis l'intégralité, ajuste les estimations.

---

## Pointeurs

- Spec sous-projet A : [docs/specs/2026-05-21-hmm-core-design.md](specs/2026-05-21-hmm-core-design.md)
- Plan d'implémentation A : [docs/plans/2026-05-21-hmm-core.md](plans/2026-05-21-hmm-core.md)
- ADR-0001 backend : [docs/decisions/0001-backend-hmmlearn-patch.md](decisions/0001-backend-hmmlearn-patch.md)
- **Spec DRAFT sous-projet B** (à brainstormer) : [docs/specs/2026-05-21-hmm-studio-web-design.md](specs/2026-05-21-hmm-studio-web-design.md)
- **Spec DRAFT sous-projet C** (à brainstormer) : [docs/specs/2026-05-21-hmm-viz-advanced-design.md](specs/2026-05-21-hmm-viz-advanced-design.md)
- CI workflow : `.github/workflows/ci.yml`
- Pre-commit config : `.pre-commit-config.yaml`
- README utilisateur : see [Home](index.md)
- Dashboard HMM existant (validation D faite, swap futur) : `C:\Users\rdenis\VScode\Experiment.Crypto.2026S1.RobinDenis\src\cmex_crypto\viz\hmm_dashboard\`
- ADR de migration côté crypto (uncommitée pour relecture) : `C:\Users\rdenis\VScode\Experiment.Crypto.2026S1.RobinDenis\notes\decisions.md` (entrée 2026-05-21)
