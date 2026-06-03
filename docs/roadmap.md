# `hmm-studio` — Roadmap complète

**Date de création** : 2026-05-21
**Auteur** : Robin Denis
**Dernière mise à jour** : 2026-06-03 (éditeur de topologie : Incrément 3 +
quick-wins clavier/marquee inventoriés ci-dessous. **Re-baseline** du 2026-06-02 : la table d'état avait
~2 semaines de retard — v1.1.0 + 69 commits non reflétés. Statuts re-synchronisés
avec le code, le CHANGELOG et le git log. Le travail livré hors-roadmap initial
— feature selection, sélection de modèles, regimes/Giudici, viz topologie animée,
wizard, param-help, expansion Academy — est désormais inventorié ci-dessous.)

> Document vivant. À ré-éditer à chaque transition de phase (fin de
> sous-projet, décision majeure, pivot). Ce n'est pas un spec — c'est la
> carte stratégique au-dessus des specs. Les specs détaillés et les plans
> d'implémentation par sous-projet vivent dans `docs/specs/`,
> `docs/superpowers/specs/` et `docs/superpowers/plans/`.

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

### Cadre : research tool *et* produit

`hmm-studio` est construit avec deux casquettes en parallèle. Les deux
informent toutes les décisions techniques et produit :

1. **Outil de recherche personnel** — premier utilisateur réel : Robin
   Denis, qui s'en sert pour modéliser des régimes (crypto / signaux
   financiers) dans son propre travail. Ce statut "first user = builder"
   garantit qu'au moins un cas d'usage est validé en permanence, mais ne
   remplace **pas** la validation par un utilisateur externe (cf. wedge
   markets section ci-dessous).
2. **Produit potentiel** — l'architecture, la doc, la licence et la
   roadmap sont pensées pour qu'un transfert vers un produit (open-source
   contribué, SaaS niche, plug-in d'éditeur scientifique) reste possible
   sans refonte structurelle. Les choix non-réversibles (licence, format
   sérialisation, schéma topologie) sont tranchés en ce sens.

---

## Positionnement stratégique 2026

> Section honnête sur ce que vaut un outil HMM en 2026. À relire à chaque
> revue trimestrielle. Si la conclusion change, la roadmap aussi.

### Pourquoi les HMM en 2026 ? Le marché honnête

Sur la modélisation séquentielle généraliste, les HMM se font écraser :

- **Transformers** (séquences discrètes, NLP, signaux longs) dominent dès
  que le volume de données est là.
- **State-space models** (Mamba, S4, Hyena) recouvrent une grande partie
  du domaine "séquences continues longues" avec un meilleur scaling.
- **Bayésien général** (Stan, PyMC, NumPyro) couvre les cas où
  l'interprétabilité prime, avec un modèle plus expressif.

**Conclusion lucide** : TAM des HMM = petit et stable, *pas en
croissance*. Le projet ne vise donc **pas** à concurrencer les modèles
neuronaux de séquence. Il s'inscrit dans une stratégie de niche.

### Les niches où les HMM restent dominants

| Niche | Pourquoi HMM gagne | Outils dominants existants |
|---|---|---|
| Speech recognition (legacy + edge) | Latence, ressources limitées, modèles très matures | Kaldi, HTK |
| Bioinformatique (séquences/motifs) | Interprétabilité requise + standards de publication établis | HMMER, GeneMark, profile-HMM |
| Maintenance prédictive industrielle | Petits datasets, états discrets explicables aux opérateurs | Solutions propriétaires + scikit-learn ad hoc |
| Quant finance (régimes) | Interprétabilité réglementaire, faible volume de données | Implémentations maison + `hmmlearn` |
| Recherche académique / enseignement | Modèle pédagogique canonique, attendu dans les cours ML/bioinfo | Notebook Jupyter + `hmmlearn` à la main |

### Paysage compétitif (qui fait quoi déjà)

| Outil | Position | Ce qu'il fait bien | Ce qu'il ne fait pas |
|---|---|---|---|
| `hmmlearn` | Moteur Python de référence (scikit-learn-style) | EM stable, API claire, mature | Pas d'UI, pas de contraintes structurelles, upstream peu actif |
| `pomegranate` | Réécriture PyTorch, plus moderne | Multi-distrib, GPU possible | Pas d'éditeur visuel, API a beaucoup changé entre v0.x et v1.x |
| `dynamax` | HMM/LDS en JAX | Performant, GPU/TPU, recherche | Pas d'UI, audience chercheurs |
| `pyhsmm` | Bayésien HDP-HMM | Modèles non-paramétriques | Niche, abandonnware |
| Stan / PyMC | Bayésien général | Très flexible | Courbe d'apprentissage abrupte, pas spécialisé HMM |
| HMMER | Bioinfo profile-HMM | Standard du domaine | Mono-usage (alignement biologique) |
| Kaldi | Speech recognition | Standard industriel | Mono-usage (speech), barrière technique élevée |

**Le trou de marché** : aucun outil ne combine (a) un éditeur **visuel** de
topologie, (b) du **Baum-Welch contraint** (left-right, branching, lifecycle)
out-of-the-box, et (c) un livrable utilisable **sans écrire de Python**.
C'est notre wedge.

### Phrase de positionnement officielle (révisée 2026-05-22 PM via ADR-0012)

> *"hmm-studio is the deepest HMM library in the Python scientific stack —
> pip-installable, sklearn-compatible, Jupyter-native, with optional
> standalone GUI for non-Python users. We don't replace your research
> environment ; we slot in as the HMM specialist."*

### Stratégie de distribution : hybride (HMM specialist + integration surface)

Décision tranchée le 2026-05-22 PM ([ADR-0012](decisions/0012-distribution-strategy-hybrid.md)) :
`hmm-studio` reste **spécialiste HMM dans son core**, ET investit dans des
**surfaces de distribution** vers les plateformes matures qui distribuent
déjà l'écosystème scientifique Python.

**Surfaces de distribution prioritaires** :
1. **I.1 Jupyter rich displays + notebook gallery** (~2-3 j) — chaque
   chercheur utilise un notebook ; on devient native dedans
2. **I.2 scikit-learn-compatible API** (~3-5 j) — entre dans les
   pipelines sklearn existants automatiquement
3. **I.3 PyMC / NumPyro bridge** (gated sur A.6) — audience bayésienne
   académique

**Précédents stratégiques qui ont survécu** : Stan (PyStan / brms), HMMER
(intègre Pfam), scikit-learn (foundation pour pandas / xgboost / etc.),
NumPy (foundation pour la stack scientifique).

**Test de validation pour toute nouvelle feature** :
> Le matin où un chercheur en éco découvre hmm-studio, comment l'utilise-t-il ?
> - ✅ `pip install hmm-studio` → ouvre un notebook → productif en 5 min
> - ❌ Doit installer une app web séparée et apprendre un nouvel environnement

### Stratégie : la pince à trois mâchoires

Plutôt que viser large, `hmm-studio` cible explicitement trois segments où
l'éditeur visuel + les contraintes structurelles font une vraie différence :

1. **Recherche académique** — chercheurs (économétrie, sciences sociales,
   biologie quantitative, ingénierie) qui ont besoin d'un HMM contraint
   *publication-ready* sans coder. Wedge : `CITATION.cff`, exemples canon,
   figures publication-ready (C.4 dans Phase C).
2. **Enseignement** — TP de cours ML / NLP / bioinfo. Wedge : Viterbi
   colorisé en live + replay temporel (C.2) = outil pédagogique sans
   équivalent. Bas coût d'acquisition : "use it for one class, students
   already know it".
3. **Praticien industriel niche** (maintenance prédictive, quant régimes)
   qui veut un outil *interprétable* (audit, conformité) plutôt qu'un
   transformer black-box. Wedge : contraintes structurelles + heatmaps
   explicables.

Hors-cible explicite : NLP grand public, speech recognition (Kaldi
domine), bioinfo profile-HMM (HMMER domine). Ne pas y aller.

### Critères de succès / d'échec (pour ce positionnement)

À 6 mois post-livraison de B (MVP web) :

- **Signal positif** : ≥ 3 utilisateurs externes réguliers (au-delà de
  Robin), ≥ 1 citation académique, ≥ 1 retour qualitatif "j'aurais voulu
  ça plus tôt".
- **Signal négatif** : 0 utilisateur externe, 0 issue GitHub, 0
  download/clone organique. → Pivot ou archivage.
- **Kill criteria** : si à M3 + 6 mois on est dans le signal négatif et
  que Robin n'utilise plus l'outil lui-même → archiver proprement (pas
  d'acharnement).

### Risques stratégiques (au-dessus des risques techniques)

| Risque | Probabilité | Mitigation |
|---|---|---|
| `hmmlearn` upstream meurt ou stagne définitivement | Moyenne (déjà sleepy) | Abstraction backend livrée 2026-05-22 → on peut basculer sur pomegranate / dynamax / impl pure-numpy sans casser l'API publique |
| Pas d'utilisateur externe à M3 + 6 mois | Élevée (par défaut) | Démo vidéo + 5-10 exemples canon + outreach minimal (Reddit r/MachineLearning, Twitter académique, mailing list bioinfo) au moment du ship B |
| Un concurrent direct apparaît | Faible (niche peu attractive) | Vélocité d'exécution, focus wedge enseignement (peu défendable mais peu attaqué) |
| Robin perd l'usage de son propre cas (crypto régimes) | Faible mais critique | Maintenir Phase D (dashboard crypto) comme test E2E permanent : c'est notre canary |
| Licence MIT trop permissive si commercialisation future | Faible | Ré-licencier les nouvelles versions reste possible (le passé reste MIT) ; documentation explicite si pivot SaaS |
| **Scope creep "unifier tous les modèles séquentiels"** (refus 2026-05-22) | Moyenne (séduisant intellectuellement) | Garde-fou explicite : toute extension qui sort du HMM-land doit passer le gating de A.6 minimum (signal externe avant build). Refuser le compilateur multi-paradigme tant qu'on n'a pas 50+ utilisateurs sur le wedge actuel. |

---

## Vue d'ensemble — où on en est

État au **2026-06-02**. Versions : v1.0.0 (2026-05-22), v1.1.0 (2026-05-23),
puis **69 commits non publiés** (vague post-v1.1, voir CHANGELOG `[Unreleased]`).
Santé : **411 tests** sur 31 fichiers, coverage ≥ 92 % sur `src/hmm_core/`.

```
ENGINE — hmm_core
  ID    Sous-projet                          Statut        Livré / note
  ───────────────────────────────────────────────────────────────────────────────
  A     hmm-core (engine + CLI)              SHIPPED v0.1  2026-05-21
  A.1   NHMM (fit_nhmm, A_t)                 SHIPPED v0.2  2026-05-22
  A.5   HMMBackend abstraction (ADR-0003)    SHIPPED       2026-05-22
  A.7   Supervisé (MLE closed-form)          SHIPPED v1.0  2026-05-22  ← était "PLANNED"
  A.7.1 Semi-supervisé (E-step clamp)        SHIPPED       states= avec NaN/-1
  A.8   Per-state EmissionSpec init hints    SHIPPED v1.0  2026-05-22
  A.9   Dirichlet priors sur transitions     SHIPPED v1.0  2026-05-22
  A.10  GMM-NHMM (2-stage)                    SHIPPED v1.1  2026-05-22  ← était "PLANNED"
  A.13  Factorial NHMM (2-stage)             SHIPPED v1.1  2026-05-22  ← était "PLANNED"
  A.6   Bayesian backend (PyMC NUTS)         SHIPPED v1.1  2026-05-26  ← était "NOT STARTED"
  A.11  Hierarchical HMM (HHMM)              SPEC-ONLY      code gated (signal externe)
  A.12  Profile-HMM (bioinfo)               DEFERRED        hors wedge

FEATURES & SÉLECTION — post-v1.1, hors-roadmap initial (voir § dédié plus bas)
  —     Unsupervised feature selection       SHIPPED       features.py (NMI medoid),
        + prep op select_features_unsup.                   spec 2026-05-27
  —     dcor distance-correlation variant    PLANNED       plan+spec 2026-05-28, 0 code
  —     Model-variant selection              SHIPPED       selection.py (compare_models,
        (HQIC, auto_grid, ModelComparison)                 HQIC), spec 2026-05-27
  —     Regime labelling + Giudici 2020      SHIPPED       regimes.py + preset YAML

DATA PREP
  B.11  Prep recipes engine + ops            SHIPPED       2026-05-22 ; ops étendus
        (21+ ops : log1p, drop_low_var…)                   (Valentin ETH port)

WEB UI — hmm_studio
  B     Studio web MVP                        SHIPPED v1.0  editor+fit+results+scan
  B.4.x Per-state / per-edge panels           SHIPPED v1.0  init hints + Dirichlet
  B.10  Data warehouse + settings page        SHIPPED       2026-05-25
  C     Visualisations avancées C.1-C.6       SHIPPED v1.0  breathing/replay/export…
  —     Topology viz P1+P2                    SHIPPED       flèches éditeur + graphe
        (transition graph animé)                           transmat animé + Observed data
  —     /compare page (BIC/AIC/HQIC grid)     SHIPPED       post-v1.1
  —     Guided creation wizard                SHIPPED       /topology/new (5 étapes)
  —     Param help tooltips (? popovers)      SHIPPED       deep links Academy

DISTRIBUTION — Phase I
  I.1   Jupyter rich displays                 SHIPPED       2026-05-26 (_repr_html_)
  I.2   scikit-learn API (HMMClassifier)      SHIPPED       2026-05-26 (estimator_checks)
  I.3   PyMC bridge                           SHIPPED v1.1  2026-05-26
  I.4+  MLflow/VSCode/Streamlit/HF/KNIME     DEFERRED       gated sur demande externe

ACADEMY (E) + VALIDATION (V)
  E     Academy : web lessons + notebooks     SHIPPED       14 leçons + quiz/flashcards
        + bibliographie + notebook bubbles                 + sections (L15 in-flight)
  V     Scientific validation V.1-V.6+perf    SHIPPED       2026-05-22

CROSS-CUTTING — Phase Z + D
  D     Migration dashboard crypto            SHIPPED       2026-05-22 (délégué)  ← détail § disait "NOT STARTED"
  Z.1   CI GitHub Actions + pre-commit        SHIPPED       2026-05-22
  Z.2   Doc site mkdocs + guides + CHANGELOG  SHIPPED       2026-05-26
  Z.5   Licence MIT + CITATION.cff            SHIPPED       2026-05-22
  Z.3   Release PyPI publique                 🔴 BLOCKED    Trusted Publisher jamais
                                                            enregistré — wheel v1.1
                                                            sur Actions, pas sur PyPI
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

> Le graphe ci-dessus est le plan d'origine (A→B/D→C). Il est **historique** :
> A→E (Phase D), B, C, V, I.1-I.3 sont tous livrés. Le travail s'est depuis
> déplacé vers les surfaces de distribution (Phase I) et l'outillage crypto
> (feature selection, sélection de modèles, regimes), pas vers de nouveaux
> nœuds du graphe initial.

---

## État au 2026-06-02 — ce qui reste *vraiment*

> Section ajoutée au re-baseline. C'est la réponse courte à « il reste quoi ? ».
> Presque tout le roadmap d'origine est livré (cf. table ci-dessus). Le reste
> se range en 4 paquets, du plus actionnable au plus stratégique.

### 1. En cours (working tree, non commité)

- **Academy — leçon 15 « Choosing the emission distribution »**
  ([plan](superpowers/plans/2026-05-28-academy-emission-lessons.md),
  [spec](superpowers/specs/2026-05-28-academy-emission-lessons-design.md)).
  Le fichier `lesson-15-choosing-emission.tsx` existe, est enregistré dans
  `lessons/index.ts`, cross-link depuis la leçon 14 ajouté. **Essentiellement
  fini — à builder + committer.**

### 2. Planifié, zéro ligne de code

- **`dcor` distance-correlation pour la feature selection**
  ([plan](superpowers/plans/2026-05-28-features-dcor-criterion.md),
  [spec](superpowers/specs/2026-05-28-features-dcor-criterion-design.md)).
  Ajoute un critère distance-correlation (capte les dépendances non-monotones
  que la NMI rate) en alternative à `unsupervised_feature_selection`. Plan TDD
  écrit le 2026-05-28 ; **rien commencé** (pas d'extra `[dcor]` dans
  `pyproject.toml`, rien dans `features.py`). **Seul backlog code prêt à exécuter.**

### 3. Gardé au chaud volontairement (ne PAS construire sans déclencheur)

- **A.11 HHMM** — spec écrite, code *gated* (≥ 1 prof/chercheur le demande
  + Academy adoptée + A.10/A.13 stables). Leçon 12 (theory-only) déjà shippée.
- **A.12 Profile-HMM** — *deferred*, hors wedge (HMMER domine la bioinfo).
- **I.4+** (MLflow flavor, extension VS Code, Streamlit, HF hub, KNIME) —
  gated sur demande externe.
- **F.2 dcor** est en paquet 2 (engagé via plan), pas ici.
- Appendix « variantes hors-scope » (AR-HMM, Coupled, CTMC, Switching SSM…) —
  rejetées/déférées avec conditions de réactivation documentées.

### 4. Dette release & hygiène (le vrai goulot de livraison)

- 🔴 **Publication PyPI bloquée** — le *Trusted Publisher* n'a jamais été
  enregistré ([release-checklist.md § Outstanding for v1.1.0](release-checklist.md)).
  Le wheel v1.1.0 est sur GitHub Actions mais **pas sur PyPI**. Étape manuelle
  unique sur `pypi.org/manage/account/publishing/`. **Tant que ce n'est pas
  fait, `pip install hmm-studio` — le cœur du positionnement ADR-0012 — ne
  marche pas.**
- 🟠 **69 commits non publiés** depuis v1.1.0, pas de tag v1.2. La vague
  post-v1.1 (feature selection, sélection de modèles, viz topologie, wizard,
  param-help, Academy 7→14 leçons) mérite une release `v1.2.0` une fois PyPI
  débloqué.

### 5. Le vrai arbitrage stratégique (pas du code)

Le positionnement (ADR-0012) et les *kill-criteria* reposent tous sur
**l'adoption externe** : ≥ 3 utilisateurs externes réguliers, ≥ 1 citation
académique à **M3 + 6 mois**. À ce jour : **0 utilisateur externe** (premier
user = Robin). Les garde-fous anti-scope-creep du projet sont explicites :
*ajouter des features sans signal externe est la mauvaise décision*. Le levier
le plus rentable n'est donc pas un nouveau variant HMM, mais **débloquer PyPI
puis faire de l'outreach** (Reddit r/MachineLearning, Twitter académique,
mailing lists). Cf. § Critères de succès / d'échec et les *kill-criteria* des
phases E et I.

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
  Prérequis de **C**. ✓ SHIPPED 2026-05-22.
- **A.2** : Support multi-séquences via `lengths` dans `fit()` et `init.*`.
- **A.3** : Pin `hmmlearn>=0.4` quand sortie (re-tester les 4 sous-classes
  contraintes).
- **A.4** : Coverage gap fixes (multinomial-kmeans path + covariances
  non-full).
- **A.5** : Abstraction `HMMBackend` — protocole + registry + backend
  hmmlearn par défaut. Décou­ple `hmm-core` du seul moteur hmmlearn et
  prépare le terrain pour pomegranate / dynamax (JAX/GPU) /
  numpy-natif sans casser l'API publique. ✓ SHIPPED 2026-05-22 (10
  tests dédiés, 76/76 total, coverage 92%).
- **A.7** : **Modes d'entraînement supervisé et semi-supervisé**
  (`fit(topo, X, states=...)`). Aujourd'hui le code est 100 %
  non-supervisé (Baum-Welch only). Élargit le périmètre d'usage à
  l'enseignement, la bioinfo, et les cas industriels avec labels
  partiels. Prioritaire **avant A.6** (cf. fiche détaillée ci-dessous).

### A.5 — Détail du backend abstrait (livré)

**Pourquoi maintenant** : un risque stratégique listé en haut de la
roadmap est qu'`hmmlearn` upstream meurt. L'abstraction *avant* que B
(web UI) ne se branche sur l'API public permet de basculer de moteur sans
breaking change pour les utilisateurs futurs.

**Surface livrée** dans `src/hmm_core/backends/` :
- `_protocol.py` : `HMMBackend` Protocol (runtime-checkable) +
  `BackendFitResult` dataclass.
- `_registry.py` : `register_backend()`, `get_backend()`, `list_backends()`.
- `hmmlearn_backend.py` : `HmmlearnBackend` qui encapsule la logique
  d'instanciation des `Constrained*HMM` + appel `.fit()`. Seul module du
  package qui dépend (transitivement) d'`hmmlearn`.

**Impact sur l'API publique** : ajout d'un paramètre optionnel
`backend: HMMBackend | str | None = None` à `fit()`. Comportement par
défaut strictement identique (76 tests passent sans modification de la
suite existante).

**Backends candidats à plus tard** (à implémenter quand le besoin
émerge, pas avant) :
- `PomegranateBackend` — utile si pomegranate v1.x (PyTorch) stabilise
  son API et si on veut du GPU.
- `DynamaxBackend` — utile pour la perf sur très longues séquences
  (JAX/jit) et pour les utilisateurs recherche/HPC.
- `NumpyBackend` — implémentation pure-NumPy de référence; sert de
  filet de sécurité si hmmlearn devient non-installable et permet
  d'expérimenter des variantes (HMM bayésien, contraintes molles, etc.).
- `BayesianHMMBackend` (PyMC / NumPyro) — voir Phase A.6 ci-dessous.

---

## Phase A.7 — Modes supervisé et semi-supervisé

**Status** : ✅ SHIPPED v1.0 (2026-05-22) — supervisé closed-form + semi-supervisé
(A.7.1, clamp E-step) livrés ; `fit(topology, X, states=...)` opérationnel. *(était : PLANNED · prioritaire avant A.6)*
**Dépend de** : A.5 (abstraction backend, livrée)
**Effort estimé** : ~1 semaine

### Pourquoi maintenant

Le code aujourd'hui est **100 % non-supervisé** par construction : `fit()`
ne prend que des observations, Baum-Welch tourne sur des états entièrement
latents. C'est un trou réel dans le périmètre d'usage, identifié par
audit le 2026-05-22 (aucune mention de "supervised" / "unsupervised" /
"labeled" nulle part dans le repo avant cette session).

**Trois raisons pour lesquelles c'est bloquant pour le wedge** :

1. **Enseignement** — La version supervisée est *toujours* introduite avant
   Baum-Welch dans un cours HMM (juste du comptage, pédagogiquement
   limpide). Sans elle, `hmm-studio` n'est pas utilisable pour enseigner
   les bases. Or l'enseignement est une des trois mâchoires du wedge.
2. **Bioinformatique** (HMMER-style profile HMM) — Construits depuis des
   alignements multiples = données labelées. Marché niche mais réel.
3. **Industrie / quant** — La réalité industrielle est **semi-supervisée**
   plus que purement non-supervisée : quelques pannes annotées par les
   opérateurs, quelques régimes labelés à la main par l'analyste, le reste
   à inférer. Notre roadmap suppose implicitement des données nues, ce qui
   est l'exception, pas la règle.

### Math (rappel pour éviter de réinventer)

| Mode | Données | Algorithme | Convergence |
|---|---|---|---|
| Non-supervisé (Baum-Welch) | `X` seul | EM itératif | itératif, sensible à l'init |
| **Supervisé** | `(X, z)` complet | MLE direct : compte `n_ij` (transitions `i→j`) et stats d'émission par état | une passe, déterministe |
| **Semi-supervisé** | `(X, z)` avec `z` partiellement `NaN` | EM contraint (positions labelées fixées dans l'E-step) ou Viterbi training | itératif, plus rapide que pur EM (moins d'entropie à résoudre) |

Pas de magie : le supervisé est strictement plus simple que ce qu'on a
déjà. Le semi-supervisé est une variante 5-10 lignes d'un E-step contraint.

### Surface proposée

**API publique** :
```python
fit(
    topology,
    X,
    *,
    states: np.ndarray | None = None,   # None → unsupervised (today),
                                         # tableau int avec NaN → semi-supervised,
                                         # tableau int complet → supervised
    seed=None, lengths=None, backend=None,
)
```

**Backend abstraction** : ajouter `fit_supervised(...)` au `HMMBackend`
Protocol. Implémentation triviale (numpy pur, pas besoin d'hmmlearn) — c'est
le **premier endroit où l'abstraction backend rapporte vraiment**, car
on n'a plus à passer par EM pour ce mode.

**CLI** : `hmm-fit run topo.yaml data.csv --labels states.csv` (optionnel).
Le fichier `states.csv` accepte des entiers (indices d'état) et des valeurs
manquantes pour le semi-supervisé.

**YAML topologie** : aucun changement. La topologie est indépendante du
mode d'entraînement.

### Tests minimum

- `test_supervised_fit_converges_in_one_pass` — `n_iter_actual == 1`.
- `test_supervised_matches_count_matrix` — vérifier que `transmat_` matche
  un comptage manuel sur un jeu jouet.
- `test_supervised_respects_mask` — interdire des transitions, vérifier
  qu'elles ne sont pas comptées (ou levée d'erreur explicite si données
  inconsistantes avec la topologie).
- `test_semisupervised_5050` — moitié labelée moitié non, vérifier que les
  positions labelées sont **dures** dans le résultat (le posterior à ces
  positions doit être one-hot).
- `test_semisupervised_converges_faster_than_full_em` — itérations < pure
  Baum-Welch sur le même problème.

### Risques

| Risque | Mitigation |
|---|---|
| `hmmlearn` ne supporte pas le supervised nativement | Pas un problème : on l'implémente côté backend en numpy (math triviale). C'est même mieux : pas de dépendance upstream pour ce mode. |
| API ambiguë (`states` = labels durs ou priors ?) | Choisir une sémantique unique : `states` = labels durs (one-hot quand fournis). Le cas "priors mous" est hors-scope, et serait du Bayésien (cf. A.6). |
| Inconsistance données ↔ topologie (un label `z_t=3` alors que `n_states=2`) | Validation stricte en début de `fit()`. Erreur explicite avec ligne fautive. |

### Définition de "done" pour A.7

- API `fit(topo, X, states=...)` documentée dans le README + docstring.
- 5 tests passent, coverage maintenue ≥ 92 %.
- CLI `hmm-fit run --labels` fonctionnel sur un exemple supervisé canonique
  (ajouter `examples/data_pos_tagging.csv` ou équivalent simple).
- Section "Training modes" dans le README avec un exemple côte-à-côte
  supervised vs unsupervised sur le même topology YAML.

---

## Phase A.10 — GMM-NHMM (GMM emissions + covariate-dependent transitions)

**Status** : ✅ SHIPPED v1.1 (2026-05-22) via décomposition 2-stage dans `src/hmm_core/gmm_nhmm.py`. L'expansion K·M (Stratégie A) a été **rejetée à l'implémentation** (sur-paramétrée sans contrainte de factorisation) — voir spec. 7 tests + 5 cross-checks V.5 verts. *(était : PLANNED)*
**Dépend de** : A.1 (NHMM livré), A.5 (abstraction backend livrée), V (validation suite — livrée avant A.10)
**Effort estimé** : 1-2 semaines

> Spec complet : [docs/specs/2026-05-22-phase-a10-gmm-nhmm.md](specs/2026-05-22-phase-a10-gmm-nhmm.md)

### Pourquoi A.10 existe

Le besoin moteur vient du dashboard crypto de Robin (Phase D). Aujourd'hui :
- Un NHMM standard force le choix entre **"un régime bull"** (perte
  d'information sur les sous-modes) et **"deux régimes bull distincts"**
  (transitions bull-low-vol → bull-high-vol modélisées comme transitions
  de régime, ce qui dilue la sémantique régime/sous-mode).
- En réalité un régime **"bull"** a souvent deux sous-modes :
  *smooth uptrend* (μ=+0.5 %/j, σ=1 %) et *explosive squeeze* (μ=+2 %/j,
  σ=4 %). Les deux appartiennent au même régime macro mais diffèrent
  microscopiquement.

**GMM-NHMM modélise exactement ça** : chaque état (régime) a un GMM en
émission (M composantes capturant les sous-modes intra-régime), et les
transitions entre régimes restent covariate-dependent (NHMM standard).

### État de l'art (audit 2026-05-22)

Aucun outil Python ne fait GMM-NHMM proprement :
- `hmmlearn` GMMHMM : GMM oui, NHMM non
- `sequentia` : GMM oui, NHMM non
- IOHMM (Mogeng) : NHMM oui, GMM non
- GaussianIOHMM : NHMM + Gaussian, GMM en placeholder non livré
- R package `NHMM` (CRAN) : a tout, mais R (pas notre stack)

**Le trou produit est réel**. Notre wedge tient.

### Approche : Stratégie C hybride

| Phase | Approche | Effort |
|---|---|---|
| **MVP** | Stratégie A : expansion K·M (chaque état k → M sous-états (k,1)..(k,M) avec mask block-structured) | 3-5 jours |
| **Validation V.5** | Cross-check Stratégie A vs Stratégie B (impl directe pure-numpy) sur jouets canoniques | 1-2 jours |
| **Refactor optionnel** | Stratégie B : GMM-NHMM direct via `NumpyGMMNHMMBackend` (E-step avec 2 niveaux de latence) | 1 semaine — seulement si MVP s'avère trop limité |

### Limites identifiabilité (documentées en spec)

- $K \leq 4$, $M \leq 3$ en MVP (au-delà : sur-paramétrisation sur crypto)
- Régularisation L2 sur coefficients TVTP
- Multi-start (5-10 init aléatoires) + sélection log-likelihood
- Contrainte d'identification : états ordonnés par $\mu_{k,1}$ croissant
- BIC pour sélection $(K, M)$

### Ce que A.10 n'est PAS

- Pas une généralisation vers GMM-SSM ou GMM-Transformer (anti-scope-creep)
- Pas un nouveau backend complet : c'est une extension de l'API existante
  (`emission.type: gmm` + `transitions.type: covariate` simultanés)
- Pas du Bayésien : MAP point estimate seulement. Le Bayésien GMM-NHMM
  est une intersection de A.6 (gated) et A.10, à reporter à plus tard.

### Définition de "done" pour A.10

- [ ] API publique : `fit(topology, X, covariates=...)` accepte
      `emission.type='gmm'` quand `transitions.type='covariate'`
- [ ] Stratégie A (K·M expansion) implémentée et testée
- [ ] Suite V.5 dédiée : 3-4 tests cross-check stratégies A vs B
- [ ] Tests de récupération sur synthétique GMM-NHMM (loi des grands nombres)
- [ ] Tests d'identifiabilité (label switching robuste)
- [ ] Intégration dashboard crypto (Phase D) : démontrer un gain de
      log-likelihood vs NHMM standard sur données BTC réelles
- [ ] Section README "GMM-NHMM for multimodal regimes" avec exemple crypto

---

## Phase A.13 — Factorial NHMM (D chaînes parallèles)

**Status** : ✅ SHIPPED v1.1 (2026-05-22) via décomposition 2-stage dans `src/hmm_core/factorial_nhmm.py`. L'expansion joint-state ∏K_d (Stratégie A) **rejetée** (même motif que A.10). 14 tests + 5 cross-checks V.6 verts ; 27× d'économie de paramètres à D=3 K=3. *(était : PLANNED)*
**Dépend de** : A.1 (NHMM ✓), A.5 (backend abstraction ✓), V (validation suite), A.10 (GMM-NHMM — partagent l'infra Strategy A)
**Effort estimé** : 2-3 semaines

> Spec complet : [docs/specs/2026-05-22-phase-a13-factorial-nhmm.md](specs/2026-05-22-phase-a13-factorial-nhmm.md)

### Pourquoi A.13 existe

Le crypto a **plusieurs dimensions de régime qui évoluent indépendamment** :
- Trend regime : {bear, range, bull}
- Volatility regime : {low-vol, normal, high-vol}
- Macro regime : {risk-on, risk-off}

Modéliser ces 3 dimensions comme un seul HMM à 3×3×2 = 18 états force
des transitions synchrones (toutes les dimensions changent en même temps
ou aucune), ce qui est **faux empiriquement** : la vol peut spiker sans
que le trend ne change, et vice-versa.

**Factorial HMM** modélise D chaînes de Markov **indépendantes** générant
conjointement les observations. Chaque chaîne a sa propre matrice de
transition, ses propres covariates. C'est mathématiquement et
sémantiquement plus correct pour ce cas.

### Math en bref

- D chaînes : $z^{(d)}_t \in \{1, \dots, K_d\}$ pour $d \in [D]$
- Transitions indépendantes : $A^{(d)}_{ij}(u^{(d)}_t)$ par chaîne
- Émission jointe : $p(x_t \mid z^{(1)}_t, \dots, z^{(D)}_t)$ — Gaussien
  paramétré par $(z^{(1)}, \dots, z^{(D)})$ ou additif Ghahramani-style
- Espace d'états joint : $\prod_d K_d$ mais paramétrisation en $O(\sum_d K_d^2)$

### Stratégie d'implémentation : C hybride (cohérent avec A.10)

- **MVP Strategy A** : encoder le HMM joint à $\prod K_d$ états avec
  **transition matrix factorisée** via mask block-structured. Réutilise
  toute l'infra A.1 + A.5 + A.10.
- **Strategy B** : `NumpyFactorialHMMBackend` avec inférence variationnelle
  mean-field structurée (Ghahramani & Jordan 1997). Sert d'oracle pour
  V.6 cross-check + débloque les cas $D \geq 4$ ou $K_d \geq 5$.

### Limites identifiabilité

- $D \leq 3$, $K_d \leq 3$ en MVP (au-delà : Strategy A trop coûteux,
  passer à Strategy B variationnelle)
- Même contraintes que A.10 sur covariates : $P_d \leq 6$ par chaîne
- T $\geq 200 \cdot$ free_params

### Définition de "done"

- [ ] API : `topology.type = "factorial"` avec `chains: [topo1, topo2, ...]`
- [ ] Strategy A (joint state expansion) livrée
- [ ] Strategy B (`NumpyFactorialHMMBackend`) livrée comme oracle
- [ ] V.6 cross-check Strategy A vs B
- [ ] Tests de récupération synthétique
- [ ] Démo crypto : trend + vol + macro, BIC vs HMM unique 18-état
- [ ] ADR-0009 sur factorisation joint state vs variationnel

---

## Phase A.11 — Hierarchical HMM (HHMM) — *spec drafted, code gated*

**Status** : SPEC-ONLY (code GATED sur signal externe explicite)
**Dépend de** : A.5 (backend abstraction ✓)
**Effort estimé code** : 3-4 semaines · **Effort actuel** : 0 (spec only)

> Spec complet : [docs/specs/2026-05-22-phase-a11-hhmm.md](specs/2026-05-22-phase-a11-hhmm.md)

### Pourquoi spec sans code

HHMM modélise des données **multi-échelle** (phonèmes → syllabes → mots ;
gestes → mouvements → actions ; micro-régimes → macro-cycles). C'est un
modèle canonique en bioinfo et en speech, mais aucun outil Python ne
l'implémente proprement.

**Notre position** :
- Le spec est rédigé pour montrer la profondeur de la pensée (marketing
  + crédibilité académique)
- L'implémentation est **gated** : ne démarre que si un utilisateur
  externe (prof, chercheur) demande explicitement
- C'est cohérent avec la discipline anti-scope-creep (hmm-studio-scope-discipline) :
  spec ≠ engagement

### Critère d'entrée code (gating)

A.11 ne démarre **que si TOUS** :
1. ≥ 1 utilisateur externe (prof/chercheur) demande explicitement HHMM
2. Phase E (Academy) shippée et adoptée (preuve que le wedge enseignement
   marche)
3. A.10, A.13 stables (parce qu'ils mobilisent le même type d'effort
   recherche)

Si ces 3 ne sont pas réunis : spec reste documentation, code reste non
écrit. C'est OK.

---

## Phase A.12 — Profile-HMM (bioinformatique) — *DEFERRED*

**Status** : DEFERRED (pas dans le wedge actuel)
**Effort estimé code** : 2-3 semaines + 1-2 sem formats bio
**Réévaluation** : post-M3+6mois ou si signal bio explicite

### Pourquoi pas maintenant

Profile-HMM est *le* modèle canonique en bioinformatique (HMMER, Pfam,
HHsuite). Si on voulait pénétrer ce marché, ce serait la porte d'entrée.

**Mais** :
- La bioinfo est un sous-marché spécifique avec ses propres formats
  (Stockholm, FASTA, MSA), conventions, attentes
- HMMER domine et est gratuit/open
- Notre wedge actuel (recherche académique générique + enseignement +
  interpretability-mandate finance/industriel) ne le requiert pas

### Conditions de réactivation

- Un chercheur bio identifié demande explicitement
- OU stratégie pivote vers la bioinfo (décision business explicite, ADR
  dédiée)

Tant qu'aucune de ces conditions n'est rencontrée : ne pas investir.

---

## Phase A.6 — Backend bayésien (PyMC / NumPyro) — *option défendue, pas engagement*

**Status** : ✅ SHIPPED v1.1 (2026-05-26) — `BayesianHMMBackend` (PyMC NUTS) dans
`src/hmm_core/backends/bayesian_backend.py`, exposé via `fit(topology, X, backend="bayesian")`,
extra `pip install "hmm-studio[bayesian]"`. `arviz.InferenceData` sur `backend.last_idata_`.
12 tests verts. Sert aussi de pont I.3 (notebook 09). *(était : NOT STARTED — le gating
signal-externe a finalement été court-circuité par le pari distribution ADR-0012.)*
**Dépend de** : A.5 (abstraction backend, livrée), A.7 (modes d'entraînement, livré)

### Origine

Brainstorm 2026-05-22 d'une proposition externe ("meta-configurateur unifiant
HMM / SSM / Transformer") — voir [Décisions tranchées](#décisions-tranchées-historique)
pour le refus de la version maximaliste. Ce qu'il reste de défendable :
ajouter un backend bayésien qui fit **la même topologie HMM** via PyMC ou
NumPyro et produit une postérieure complète sur (A, π, paramètres
d'émission) au lieu d'un point MAP. C'est la "mode interprétable" que
visait la proposition, mais en restant dans le wedge HMM où la math est
propre.

### Pourquoi c'est on-strategy

- **Aucun outil existant** ne combine éditeur visuel de topologie HMM +
  fit fréquentiste + fit bayésien dans la même interface. Différenciation
  forte sans expansion de scope.
- **Ouvre le segment académique bayésien** (PyMC / Stan / NumPyro / Pyro
  utilisateurs), large et bien aligné avec le wedge "recherche".
- **Reste dans HMM-land** : pas de promesse de "compiler vers Transformer",
  pas de génération de code multi-framework, pas de problèmes de
  sémantique non-mappable. Le YAML de topologie a un sens **identique**
  des deux côtés (mêmes mask, mêmes contraintes structurelles).
- **Coût borné** : ~2-3 semaines de travail estimées, vs ~2-3 ans pour la
  version maximaliste rejetée.

### Surface proposée

- Nouveau module `src/hmm_core/backends/bayesian/` avec
  `PyMCBackend` (et éventuellement `NumPyroBackend` si demande utilisateur).
- Output enrichi (extension de `BackendFitResult`) :
  - `posterior_samples : dict[str, np.ndarray]` — échantillons MCMC sur
    A, π, paramètres d'émission.
  - `credible_intervals : dict[str, tuple[np.ndarray, np.ndarray]]` —
    intervalles à 95 % par paramètre.
  - `posterior_predictive : Optional[np.ndarray]` — pour les checks de
    cohérence.
- API publique inchangée : `fit(topology, X, backend="pymc")`.
- Visualisation (côté B / C) : heatmaps de A avec barres d'incertitude,
  posterior predictive overlay sur la séquence Viterbi.

### Critères d'entrée (gating — ne pas démarrer avant)

A.6 ne démarre **que si tous** les critères suivants sont réunis :

1. **Phase B shippée** (MVP web utilisable par un utilisateur non-Python).
2. **Au moins 1 utilisateur externe académique a contacté le projet** ou
   forké le repo (signal réel, pas hypothèse). Si zéro signal externe à
   M3 + 3 mois, A.6 reste en sommeil — c'est probable que le projet doive
   re-questionner ses objectifs plutôt qu'ajouter une feature.
3. **Robin n'est pas déjà en train de re-prioriser** vers d'autres chantiers
   plus pressants (régimes crypto, autres outils de recherche).

Si l'un de ces trois critères n'est pas rempli : A.6 reste une option
documentée, pas un engagement. **Mieux vaut ne pas la livrer que la livrer
sans demande réelle.**

### Ce que A.6 n'est PAS (rappel anti-scope-creep)

- **Pas** un "compilateur" vers Mamba / SSM / Transformer. Cf. décision
  tranchée 2026-05-22 de refus du meta-configurateur.
- **Pas** un outil de causal inference. Bayésien ≠ causal.
- **Pas** une généralisation au-delà du HMM. Si on veut faire du SwitchingSSM
  ou du DeepHMM, c'est une autre phase (potentiellement A.7), et pas
  avant A.6 livrée et adoptée.

---

## Phase B — `hmm-studio` web UI

**Status** : ✅ SHIPPED v1.0 (2026-05-22) — MVP complet : FastAPI + React/Vite/TS,
éditeur React Flow (drag-drop états/transitions, undo/redo, YAML import/export),
upload data, fit launcher + streaming WebSocket de la log-vraisemblance, K-scan,
Results (heatmap transmat, Viterbi colorisé, émissions, A(t) animé), dark mode.
Étendu depuis : warehouse (B.10), /compare, wizard guidé, param-help, viz topologie
animée. *(était : NOT STARTED)*
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

## Phase B.10 — Data warehouse local + multi-format

**Status** : ✅ SHIPPED (2026-05-25) — warehouse multi-format (CSV/parquet/JSON/Excel/feather),
6 endpoints REST + path-traversal guard, sidecar `.hmm.yaml`, settings page. *(était : PLANNED)*
**Dépend de** : B (UI socle, livré pour l'essentiel)
**Effort estimé** : 3-4 jours

> Spec complet : [docs/specs/2026-05-22-phase-b10-data-warehouse.md](specs/2026-05-22-phase-b10-data-warehouse.md)

### Pourquoi B.10 existe

Aujourd'hui, chaque fit demande un chemin CSV ; l'utilisateur gère son
filesystem sans aide. C'est invisible pour un chercheur expérimenté, mais
**friction d'onboarding** pour un newcomer et **inefficient pour la
réutilisation** de datasets.

B.10 ajoute :
- Un répertoire désigné comme "data warehouse" (configurable par
  utilisateur)
- Navigation des datasets dans le tab Data avec métadonnées (rows, cols,
  dtypes, date modif, taille)
- Sidecar `.hmm.yaml` par dataset pour provenance + colonnes annotées
- Auto-détection du format à partir de l'extension

### Scope explicite — anti-MLflow/DVC

| ✅ Inclus (MVP) | ❌ Exclu (scope creep) |
|---|---|
| Local filesystem, single warehouse dir | Multi-workspace |
| Auto-discovery par scan | Indexation DB |
| Sidecar metadata yaml | Versioning git-like |
| Multi-format (CSV/parquet/JSON/Excel/feather) | Remote storage (S3/GCS) |
| Re-utilisation cross-fit du dataset | Lineage formel / DAG |
| Refresh manuel (bouton) ou scan auto-périodique | Pipeline d'ingestion |

C'est **un explorateur de fichiers spécialisé**, pas un data engineering
platform. DVC / MLflow / Delta Lake jouent ce rôle là, on ne les
concurrence pas.

### Définition de "done"

- [ ] Configuration utilisateur expose `warehouse_path` (settings)
- [ ] Endpoint backend `GET /api/warehouse` retourne liste fichiers + meta
- [ ] Endpoint `POST /api/warehouse/refresh` re-scan
- [ ] Tab Data : sidebar navigable + preview
- [ ] Multi-format read : CSV, parquet, JSON/JSONL, Excel, feather
- [ ] Sidecar `.hmm.yaml` détecté et exposé en metadata
- [ ] Tests E2E : upload, browse, select, fit avec dataset warehouse

---

## Travaux livrés hors-roadmap initial (post-v1.1)

> Ces chantiers ne figuraient pas comme phases au roadmap d'origine : ils ont
> émergé de l'usage réel (port de la recherche crypto Nathan/Robin & Valentin)
> après v1.1.0. Inventoriés ici au re-baseline pour que le roadmap suive la
> réalité. Specs sous `docs/specs/`.

### Refonte UX de l'éditeur de topologie — Incréments 1→3 + quick-wins — ✅ SHIPPED (2026-06-03)

Suite à un retour utilisateur (« états collés, drag cassé, pas de probas sur les
flèches »). Spec : `docs/superpowers/specs/2026-06-02-topology-editor-ux-overhaul-design.md`
(designs rounds 2-3 en updates datés). Plans : `docs/superpowers/plans/2026-06-02-*` (Inc 1),
`2026-06-03-topology-editor-increment-2.md` (Inc 2),
`2026-06-03-saved-models-portability.md` (Inc 3). **60 tests vitest** (tier unitaire
frontend) + specs Playwright.

- **Incrément 1** : drag réparé (les bulles suivent le curseur, la sélection survit
  aux commits) + espacement (grille 240/160, fitView borné, largeur de pilule) +
  toggle *prior preview* (moyenne du prior, OFF par défaut).
- **Incrément 2** : (a) **ergodique** matérialise ses K² flèches ; (b) **self-loops**
  en arc + **bidirectionnelles** courbées + bouton **Tidy** (chaîne/cercle, undo
  atomique) + affordance `↺` ; (c) bouton **« Fit this topology »** dataset-gated
  (validate reste structurel) ; (d) toggle **3 états aucun/prior/appris** avec
  overlay du transmat **appris** (jointure par nom + garde anti-stale via
  fingerprint — jamais de faux chiffres) ; (e) **stop-gap modèles sauvegardés**
  (store localStorage `hmm-studio-saved-topologies` + garde « sauver avant
  d'écraser »). Stores `fitLink`/`saved`/`editorPrefs` séparés du modèle (pureté
  zundo/YAML préservée ; B2 « cacher le transmat dans le modèle » rejeté).
- **Incrément 3 — portabilité des modèles sauvegardés** : export **YAML** + **share-URL**
  par modèle, **import YAML → bibliothèque**, sauvegarde/restauration de **toute la
  bibliothèque** en JSON (`{schema_version, kind, models}`, forward-compat A1),
  panneau **« My models »** remplaçant le `<select>`. Helper pur `modelLibraryIO`,
  zéro changement backend. Spec `2026-06-03-saved-models-portability-design.md`.
- **Quick-wins (2026-06-03)** : (a) **undo/redo au clavier** Ctrl+Z / Ctrl+Y /
  Ctrl+Shift+Z — la feature undo existait *via les boutons* mais n'était bindée nulle
  part (correctif de **découvrabilité**, pas un bug de state : les drags étaient déjà
  trackés par zundo) ; (b) **sélection rectangle** au clic-gauche (`selectionOnDrag`
  + `panOnDrag=[1,2]` + `panOnScroll` — modèle « Figma » : drag = sélection, scroll =
  pan, Ctrl/⌘+scroll = zoom, **hint à l'écran** pour ne pas surprendre) ; (c) **drag
  de groupe = un seul undo** (commit batché via `setPositions`). Helpers purs
  `undoHotkey` + `nodeChangeCommit` testés ; revue adversariale 3-lentilles.
- **Différé au roadmap** : **A1 vrais onglets multi-HMM** (façade multi-document +
  barre d'onglets + undo par onglet) — avantages/risques consignés dans le spec.
- **Pistes éditeur suivantes** (diagnostiquées 2026-06-03 contre le code, à spec'er) :
  - **Wizard → choix « cet onglet vs nouveau »** — stop-gap à 3 voies réutilisant
    « My models » comme 2e slot (le wizard ne clobber déjà pas en silence ; reframe
    du prompt + boucher le chemin non-gardé `LessonPage.loadTopology`). **Pas A1.** Effort S.
  - **Lisibilité des flèches (Inc 4)** — gate des labels par zoom + survol/sélection,
    élagage `MIN_PROB` (déjà présent côté graphe Résultats), nouveau editorPref
    (persist v2). Effort M, **spec requis**.
  - **Copier-coller de nœuds (Ctrl+C / Ctrl+V)** — feature net-neuve (multi-sélection
    + action store `pasteStates` : re-mint d'ids, renommage, offset). Effort M, **spec requis**.

### Feature selection (`hmm_core.features`) — ✅ SHIPPED

- `unsupervised_feature_selection(features, n_clusters=10, ...)` — clustering
  des colonnes candidates par information mutuelle normalisée (NMI), garde un
  médoïde par cluster → sous-ensemble décorrélé prêt à `fit()`. Zéro nouvelle
  dépendance (sklearn + scipy). Porté de `cmex_crypto/features/unsupervised_selection.py`.
- Prep op `select_features_unsupervised` (utilisable en recette YAML).
- 10 tests. Spec : `docs/specs/2026-05-27-unsupervised-feature-selection.md`.
- **Suite engagée** : variante `dcor` (distance-correlation) — *planifiée, 0 code*,
  voir § « État au 2026-06-02 » paquet 2.

### Sélection de modèles (`hmm_core.selection`) — ✅ SHIPPED

- `compare_models(X, candidates, ...) -> ModelComparison` — fit chaque candidat
  sur le même `X`, classe les comparables par BIC/AIC/HQIC ; robuste (un fit qui
  lève → `error` + NaN, jamais fatal). `auto_grid()` génère la grille émission×K.
- Critère **HQIC** ajouté à `FittedModel` (à côté de BIC/AIC) + `best_k_by_hqic`
  dans le K-scan. Préféré par plusieurs papiers HMM-finance sur séries longues.
- Page web **`/compare`** (grille Gaussian/GMM/Poisson × K, classée). NHMM/Factorial
  restent Python-API / `hmm-fit compare` (non comparables : modélisent P(X|Z)).
- Spec : `docs/specs/2026-05-27-model-variant-selection.md` (Phases 1-3 livrées).

### Régimes & labelling (`hmm_core.regimes`) — ✅ SHIPPED

- `regime_order_by_feature_mean()` + `regime_labels(...)` — résolvent le problème
  « les états EM ont un ordre arbitraire » (mappe index brut → label humain par
  moyenne d'émission croissante). Porté de `regimes/giudici.py`.
- Preset `examples/giudici_2020_btc_regimes.yaml` — le HMM 3-états gaussien
  canonique de Giudici & Abu Hashish (2020) pour les régimes cryptoasset.

### Prep ops étendus + post-v1.1 quality pass — ✅ SHIPPED

- Nouveaux ops `log1p`, `drop_low_variance` ; recette `valentin_eth` (port ETH).
- Quality pass : `to_summary_dict()`/`to_summary_json()` (source unique des
  métriques) sur les 4 variants ; kmeans init GMM correct pour `full`/`tied`/`spherical` ;
  smoothing `startprob_` (pathologie strict-left-right + `first_state`) ;
  `FitSpec.freeze_startprob` / `freeze_transmat`. Helper de régression partagé
  (`tests/_regression_helpers.py`).

### UI post-v1.1 — ✅ SHIPPED

- **Wizard de création guidée** (`/topology/new`, 5 étapes Emission → States →
  Transitions → Training → Review, suggestion d'émission data-aware, preview YAML).
- **Param-help** : popovers `?` sur éditeur / Fit / Compare avec deep-link Academy.
- **Viz topologie** : flèches directionnelles dans l'éditeur + graphe transmat
  appris animé (anneau Viterbi courant, fills = posterior, edge actif surligné)
  synchronisé au player + panneau **Observed data** (`GET /api/fit/{id}/series`).

### Academy étendue (Phase E élargie) — ✅ SHIPPED / 🔄 in-flight

- 7 → 12 → 13 → **14 leçons** (L15 « choosing the emission » en working tree).
- Quiz noté + flashcards par leçon (niveaux cognitifs Recall/Apply/Analyze,
  meilleurs scores persistés). Sections thématiques ordonnées. Bulles
  `<NotebookLink />` (Binder/Colab/GitHub/download) sur 9 leçons.
- Bibliographie sourcée 4-tiers `docs/sources/academy-references.md` + composant
  `<FurtherReading />`.

---

## Phase I — Integrations (distribution surfaces vers plateformes matures)

**Status** : ✅ SHIPPED (2026-05-26) — I.1 (Jupyter), I.2 (sklearn), I.3 (PyMC bridge) tous livrés. I.4+ deferred (gated sur demande). *(était : PLANNED · PRIORITAIRE post-ADR-0012)*
**Dépend de** : A.5 (backend abstraction, livré) pour I.2
**Effort total** : ~5-8 jours (I.1 + I.2) ; I.3 gated sur A.6

> Voir [ADR-0012 — Distribution strategy hybrid](decisions/0012-distribution-strategy-hybrid.md)
> pour la décision stratégique qui a créé cette phase.

### Pourquoi Phase I existe

Suite à l'analyse stratégique 2026-05-22 PM : `hmm-studio` reste spécialiste
HMM dans son core, mais investit en parallèle dans des **surfaces de
distribution** vers les plateformes matures qui distribuent déjà
l'écosystème scientifique Python (Jupyter, scikit-learn, PyMC).

### Phrase de positionnement officielle

> *"hmm-studio is the deepest HMM library in the Python scientific stack —
> pip-installable, sklearn-compatible, Jupyter-native, with optional
> standalone GUI for non-Python users. We don't replace your research
> environment ; we slot in as the HMM specialist."*

### I.1 — Jupyter rich displays + notebook gallery (~2-3 jours)

**Status** : ✅ SHIPPED (2026-05-26) — méthodes `_repr_html_` + notebook gallery (8+ notebooks) + Binder/Colab badges.

**Surface livrable** :
- `Topology.__repr_html__()` — graphe interactif inline (D3 ou Mermaid)
- `FittedModel._repr_html_()` — heatmap transmat + Viterbi
- `NHMMFittedModel._repr_html_()` — A(t) animé inline
- `GMMNHMMFittedModel._repr_html_()` — heatmap + sub-modes per regime
- `FactorialNHMMFittedModel._repr_html_()` — per-chain breakdown
- `BenchmarkResult._repr_html_()` (quand B.12 ship) — table comparative
- `Pipeline._repr_html_()` — chaîne des steps avec preview
- **Notebook gallery officielle** sur GitHub : 5-10 notebooks canoniques
  couvrant :
  - Quickstart 30-secondes
  - Crypto regime modeling (Robin's use case)
  - Bioinfo style profile-HMM avec contraintes
  - Comparing HMM vs threshold baseline
  - GMM-NHMM submodes detection
  - Factorial NHMM multi-factor regimes

**Définition de "done"** :
- [ ] 5-7 méthodes `_repr_html_` ajoutées et stylées
- [ ] 5+ notebooks dans `notebooks/` + binder config
- [ ] Section README "Quickstart in Jupyter" en première position
- [ ] Test : `from hmm_studio import Topology ; topo` produit HTML riche

### I.2 — scikit-learn-compatible API (~3-5 jours)

**Status** : ✅ SHIPPED (2026-05-26) — `HMMClassifier` passe `estimator_checks`, intégré Pipeline/GridSearchCV. 20 tests.

**Surface livrable** :
- `hmm_studio.sklearn.HMMClassifier(n_states, topology=..., emission=..., ...)`
  — implements `BaseEstimator`, `ClassifierMixin`
  - `fit(X, y=None)` : si `y` fourni → supervised, sinon → unsupervised
  - `predict(X)` : Viterbi state labels
  - `predict_proba(X)` : forward-backward posteriors
  - `score(X, y)` : log-likelihood or classification accuracy
- `hmm_studio.sklearn.HMMRegressor` : prédit l'observation suivante
- `get_params()` / `set_params()` pour grid search compatibility
- Tests : intégration dans `Pipeline`, `cross_val_score`, `GridSearchCV`
- Documentation : section "Use with scikit-learn pipelines" avec exemple

**Définition de "done"** :
- [ ] `HMMClassifier` passe `sklearn.utils.estimator_checks.check_estimator`
- [ ] Exemple notebook : grid search sur K + topology via sklearn
- [ ] Section README "Drop-in with scikit-learn"
- [ ] Tests dans `tests/test_sklearn_compat.py`

### I.3 — PyMC / NumPyro bridge (gated sur A.6)

**Status** : OPTION · gated sur A.6 ship

**Surface livrable** :
- `hmm_studio.pymc_bridge.HMMTopologyPyMC.from_yaml(path)` — génère le
  modèle PyMC équivalent
- `hmm_studio.pymc_bridge.fit_bayesian(topo, X, n_samples=2000)` — fit
  bayésien via PyMC + retour `FittedModel` enrichi avec `posterior_samples`
- Convertit `arviz.InferenceData` → notre format
- Documentation et exemple sur la communauté bayésienne

**Effort** : 1-2 semaines, **gated sur A.6 (BayesianHMMBackend) shippé**.

### I.4+ — Deferred (gated sur signal externe)

| Extension | Pourquoi deferred |
|---|---|
| MLflow model flavor | Effort modéré, signal demandé si ML pratici­ens demandent |
| VS Code extension (YAML autocomplete topology) | Cool, mais ROI faible vs Jupyter |
| Streamlit components | Si demande pour dashboards rapides |
| Hugging Face hub | Probablement N/A — HF = transformer/generation |
| KNIME nodes | N/A — KNIME audience pas notre wedge |

### Critères de succès Phase I (à M+3 post-ship)

| Métrique | Cible |
|---|---|
| Visites uniques /mois sur notebook gallery (GitHub stars/clones binder) | ≥ 50 |
| Mentions dans notebooks tiers (Kaggle, GitHub search) | ≥ 3 |
| Issues / PRs externes liées à sklearn compat | ≥ 1 |
| Citations / utilisations en papier académique | ≥ 1 (signal fort) |

### Anti-scope-creep guardrails

- I.1, I.2, I.3 sont les surfaces concrètes. I.4+ reste gated.
- **Pas de re-build d'un IDE / notebook environnement** (Hex / Deepnote
  territory). On enrichit Jupyter existant, pas plus.
- **Pas de fork de sklearn**. On expose une API conforme à la leur, pas
  une nouvelle.
- **Pas de wrapper de PyMC complet**. On expose le pont topology → PyMC
  model, point.

---

## Phase V — Scientific validation suite

**Status** : ✅ SHIPPED (2026-05-22) — V.1-V.6 + V.perf livrés (cross-check hmmlearn, recovery synthétique, textbook canoniques Russell & Norvig / Durbin / Rabiner / Eisner, stabilité numérique, cross-checks A.10/A.13). *(était : SPEC DRAFTED)*
**Dépend de** : A (core stable, livré)
**Effort estimé** : ~3-5 jours

> Spec complet : [docs/specs/2026-05-22-phase-v-validation.md](specs/2026-05-22-phase-v-validation.md)

### Pourquoi V existe

Les 131 tests actuels testent la **correction du code** (régressions, contrats
d'API, edge cases). Ils ne testent **pas** la **correction du modèle
mathématique** sur des exemples canoniques où la réponse est connue
analytiquement ou par référence académique. C'est un trou critique pour un
outil scientifique destiné à la recherche et à l'enseignement (deux mâchoires
sur trois de notre wedge).

Le jour où un chercheur publie un papier basé sur `hmm-studio`, ou un prof
l'utilise en cours, la question "comment savez-vous que c'est correct ?"
doit avoir une réponse documentée et reproductible.

### 4 couches de validation

| Couche | Objectif | Effort | Tests visés |
|---|---|---|---|
| **V.1** Cross-check `hmmlearn` | Sanity : notre dispatcher = hmmlearn brut sur topologie ergodique | 0.5 j | 4 (un par émission) |
| **V.2** Recovery sur synthétique | Statistique : estimateur converge vers vrais paramètres quand N→∞ | 1-1.5 j | 5-6 (par émission + topologie left-right) |
| **V.3** Textbook canoniques | Analytique : reproduit Russell & Norvig (parapluie), Durbin (dishonest casino), Rabiner 1989, Eisner ice cream | 1-1.5 j | 4-6 |
| **V.4** Stabilité numérique | Robustesse : séquences longues, covariances quasi-singulières, états rares, K grand | 0.5-1 j | 4-5 |
| **V.5** Cross-check A.10 strategies (gated sur A.10 PLANNED) | Stratégies A (K·M expansion) vs B (direct GMM-NHMM) donnent mêmes résultats sur jouets canoniques | 1 j | 3-4 (Gaussian K=2 M=2, K=3 M=2, identification, etc.) |
| **V.6** Cross-check A.13 strategies (gated sur A.13 PLANNED) | Stratégies A (joint state expansion ∏K_d) vs B (variationnel mean-field) donnent mêmes résultats sur petits jouets D=2 K=2 | 1 j | 3-4 (D=2 K=2, D=2 K=3, identification) |

### Surface livrée (cible)

- Dossier `validation/` séparé de `tests/` (suite séparée, non lancée dans
  la CI quotidienne, dédiée au scientifique).
- Un fichier README dans `validation/` listant chaque test avec : source
  canonique citée, tolérance numérique, résultat attendu.
- 4-5 jeux de données fixtures dans `validation/fixtures/`.
- Badge "Validated against Russell & Norvig + Durbin + Rabiner canonical
  examples" sur le README principal (signal de qualité pour les academics).

### Gating et critères

- **Prérequis pour lancer V** : aucun bloquant (peut démarrer maintenant).
- **Définition de "done"** : les ~18-20 tests passent avec leurs tolérances
  documentées, README de validation à jour, badge ajouté au README projet.
- **Critère de re-validation** : V doit être ré-exécuté à chaque changement
  de version d'`hmmlearn` ou d'un autre backend, et à chaque release majeure.

### Risques

| Risque | Mitigation |
|---|---|
| Tolérance trop stricte → tests flakies | Documenter chaque tolérance avec sa justification (loi des grands nombres, précision flottante, etc.) |
| Coût compute des recovery tests (N=10000) | Marker pytest `@slow`, run nightly seulement |
| Discrépance avec hmmlearn sur cas extrêmes | C'est exactement ce qu'on veut détecter — si V.1 échoue, c'est un bug à fixer |

---

## Phase E — Academy (notebook gallery)

**Status** : ✅ **SHIPPED 2026-05-26** (reframe via ADR-0012)
**Dépend de** : I.1 (Jupyter rich displays ✓), V (crédibilité scientifique ✓)
**Effort réel** : ~1 jour (la majorité du contenu était déjà écrit côté I.1 et par Robin)

> Spec original : [docs/specs/2026-05-22-phase-e-academy.md](specs/2026-05-22-phase-e-academy.md)
>
> **Reframe ADR-0012 (2026-05-22 PM)** : la stratégie de distribution
> hybride a pivoté Phase E d'**onglet web académie** vers **notebook
> gallery officielle**. Plus naturel pour les chercheurs, gratuit en
> distribution via GitHub/Binder/Colab, aligné avec le positionnement
> "Jupyter-native HMM library".

### Ce qui a été livré

- **8 notebooks runnables** dans `notebooks/` couvrant la trajectoire
  complète "newcomer → praticien" :
  1. Quickstart (30 sec : Topology → fit → decode + left-right)
  2. NHMM crypto regimes (covariate-dependent transitions, A_t inspection)
  3. Data prep recipes (bundled + composition + provenance sidecar)
  4. sklearn pipeline integration (Pipeline + GridSearchCV + cross_val)
  5. GMM-NHMM sub-modes (multi-modal regimes)
  6. Factorial NHMM multi-factor (independent regime dimensions)
  7. AIMA umbrella world (canonical Russell & Norvig 14.2.2/14.2.4)
  8. Durbin dishonest casino (Biological Sequence Analysis Chap. 3)
- **Binder config** (`binder/requirements.txt` + `postBuild` + `runtime.txt`)
  → mybinder.org build runnable en un clic
- **Open-in-Binder + Open-in-Colab badges** sur `notebooks/README.md` et
  badge global dans `README.md` racine
- **Suggested learning path** dans `notebooks/README.md` (newcomer → praticien)
- **Section "Academy : zero-install learning"** dans le README racine

### Pourquoi notebook ≫ tab web académie

Évaluation post-ADR-0012 :
- **Distribution** : un notebook Binder = lien partageable, runnable en 30s, indexé Google/Kaggle
- **Friction d'install** : zéro (vs nécessite l'app web + warehouse + topology editor)
- **Updates** : un commit GitHub propage à tous les utilisateurs (vs déploiement web)
- **Workflow naturel** : les chercheurs vivent dans Jupyter, on les y rencontre
- **Coût d'investissement** : ~1 jour (vs ~1-2 semaines pour l'onglet web)

### Critères de succès (à M+3)

Inchangés par le reframe — seul le médium change :
| Métrique | Cible | Mode de mesure |
|---|---|---|
| Visites uniques /mois notebook gallery | ≥ 100 | GitHub Insights (stars/clones) + Binder analytics |
| Mentions externes | ≥ 3 | Recherche Google + Twitter + Reddit + Kaggle |
| Profs identifiés | ≥ 1 confirmé | Outreach manuel |
| Citations académiques | ≥ 1 | Google Scholar / CITATION.cff usage |

### Kill criteria

Si à M+3 : 0 mention externe ET 0 prof identifié ET Robin ne recommande pas
les notebooks à ses propres collaborateurs → archiver les notebooks
avancés (05-08), garder seulement quickstart + sklearn (le minimum vital).

### Pourquoi E existe

L'enseignement est **explicitement** une des trois mâchoires du wedge
stratégique (cf. § Positionnement stratégique 2026). C'est même la
mâchoire la plus défendable parce qu'**un prof qui adopte hmm-studio
en TP entraîne 20-100 étudiants par an** qui apprennent les HMM via
notre outil et l'utiliseront ensuite en recherche et en industrie.

Aujourd'hui : zéro contenu pédagogique intégré. Un utilisateur qui ne
connaît pas les HMM débarque sur l'éditeur de topologie et ne sait pas
ce qu'est une matrice de transition. **C'est un trou d'acquisition.**

### Surface livrée (cible MVP)

- Nouvel onglet **"Academy"** dans la navigation B (à côté de Home, Data,
  Topology editor, Fit, Results).
- 7 leçons interactives courtes (~10-15 min chacune, 1-2h total).
- Chaque leçon = HTML + MDX (markdown + composants React) + visualisations
  D3.js + composants UI réutilisés de l'éditeur.
- Chaque leçon se termine par un bouton **"Try it in the editor →"** qui
  pré-remplit l'éditeur avec un YAML d'exemple correspondant. Bridge
  apprentissage → pratique.

### Les 7 leçons

1. **"Qu'est-ce qu'un état caché ?"** — pièce truquée/honnête + slider
2. **"La matrice de transition, c'est un graphe"** — mini-éditeur 2 états
3. **"Forward algorithm : pourquoi on additionne"** — animation belief propagation
4. **"Viterbi vs Forward-Backward"** — même données, deux algos, comparaison côte-à-côte
5. **"Topologie : left-right vs ergodique"** — switcher topologie, voir l'effet
6. **"Supervised vs Unsupervised"** — toggle labels on/off
7. **"Quand NE PAS utiliser un HMM"** — honnêteté intellectuelle, pointer vers Transformer/SSM

La leçon 7 est **critique** — elle distingue un outil sérieux d'un outil
commercial qui surjoue. Elle renforce le wedge en clarifiant ce qu'on
n'est pas.

### Stack technique

- **MDX** (Markdown + React) pour le contenu — authoring accessible
- **D3.js** pour les visualisations probabilistes (simplexes, paths, animations)
- **Réutiliser** les composants existants de l'éditeur de topologie
- **NON aux Jupyter notebooks** : kernel = friction, fragiles, mauvais bridge

### Critères de succès / d'échec (à M+3 post-ship)

| Signal | Seuil | Conséquence si raté |
|---|---|---|
| Visites uniques /mois sur `/academy` | ≥ 100 | Re-tester contenu / SEO / discoverability |
| Utilisations du bridge "Try in editor" | ≥ 10 / mois | Le bridge n'est pas adopté → repenser CTA |
| Profs qui l'utilisent en cours | ≥ 1 confirmé (signal manuel) | Wedge enseignement reste théorique → repenser format |
| Mentions externes (Reddit, Twitter, blog) | ≥ 3 | Pas de bouche-à-oreille → outreach manuel nécessaire |

**Kill criteria** : si à M+3 zéro signal externe ET aucun usage interne par
Robin, archiver l'académie (la laisser en lecture seule, ne plus
investir).

### Risques

| Risque | Mitigation |
|---|---|
| Scope creep ("ajoutons 50 leçons", "ajoutons un quiz") | Critères de "done" stricts : 7 leçons, pas une de plus dans le MVP. Quiz reportés à E.2 (gated sur signal) |
| Contenu se périme quand l'UI évolue | Tests E2E Playwright sur les bridges éditeur ; régressions détectées |
| Pas le bon ton pédagogique | Faire relire les 7 brouillons par 2-3 profs / chercheurs avant ship |

---

## Phase C — Visualisations avancées + NHMM animé

**Status** : ✅ SHIPPED v1.0 (2026-05-22), étendu post-v1.1 — C.1-C.6 livrés (NHMM breathing, replay temporel, K-scan, export SVG, annotations CSV, multi-séquences) + viz topologie P1/P2 (flèches éditeur, transition graph animé synchronisé au player, panneau Observed data). *(était : NOT STARTED)*
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

**Status** : ✅ SHIPPED (2026-05-22) — le dashboard crypto délègue à `hmm_core.fit` ; drift numérique = 6×10⁻⁶ %, 9 tests de régression verts. *(était : NOT STARTED)*
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

> **Historique** — ce planning S+0..S+19 était l'estimation initiale. La vélocité
> réelle l'a largement battu : A, B, C, D, V, E, I, A.6/A.7/A.10/A.13 tous livrés
> entre le 2026-05-21 et le 2026-05-27. Conservé tel quel comme trace d'estimation.

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

- **M1** : `hmm-core` v0.1 livré — ✅ atteint 2026-05-21
- **M2** : Dashboard crypto migré, NHMM dans core, `hmm-core` v0.2 — ✅ atteint 2026-05-22
- **M3** : Studio MVP utilisable sans connaissance Python — ✅ atteint (v1.0, 2026-05-22)
- **M4** : Visualisations avancées + exemples publication-ready — ✅ atteint (C livré + viz topologie post-v1.1)
- **M5** : **v1.0/v1.1 PyPI public — 🔴 BLOQUÉ** : wheel construit (v1.1.0), mais
  Trusted Publisher jamais enregistré → jamais publié sur PyPI. C'est le jalon
  ouvert. Une fois débloqué : tagger **v1.2.0** (vague post-v1.1).
- **M6** (nouveau) : **Premier signal externe** — ≥ 1 utilisateur/citation
  externe. C'est le vrai jalon stratégique restant (cf. kill-criteria). Aucun
  feature ne le remplace ; il dépend de M5 (pip install) + outreach.

---

## Décisions ouvertes à arbitrer

La plupart des décisions ci-dessous ont été **tranchées à l'implémentation** ;
conservées avec leur résolution pour la traçabilité.

1. ~~Migration dashboard crypto avant ou après B ?~~ → **Avant** (Phase D livrée 2026-05-22). ✅
2. ~~Stack frontend de B : React Flow vs Cytoscape ?~~ → **React Flow**. ✅
3. ~~Backend persistence de B : in-memory vs SQLite ?~~ → **SQLite** (job history). ✅
4. ~~NHMM "breathing" en B ou en C ?~~ → **Animé en C** + viz topologie post-v1.1. ✅
5. **PyPI public ou private ?** → **public** (décidé), mais **publication bloquée**
   sur l'enregistrement Trusted Publisher (cf. M5). ⏳ *seule décision encore
   actionnable, et c'est de l'ops, pas un arbitrage.*
6. ~~Doc site : mkdocs vs docusaurus vs custom ?~~ → **mkdocs-material** (Z.2 livré). ✅

**Vraie question ouverte restante** (stratégique, pas technique) : *après PyPI,
qu'est-ce qui ramène un premier utilisateur externe ?* — outreach ciblé vs
attendre la découverte organique. À trancher au moment de débloquer M5.

### Décisions tranchées (historique)

| Date | Décision | Notes |
|---|---|---|
| 2026-05-22 | Licence : **MIT** | `LICENSE` + `CITATION.cff` à la racine. Ré-licenciement futur possible (les versions passées restent MIT, mais c'est acceptable). |
| 2026-05-22 | Abstraction backend : **HMMBackend Protocol** + registry, hmmlearn comme backend par défaut | Décou­ple `hmm-core` de hmmlearn. Voir A.5. |
| 2026-05-22 | Premier utilisateur officiel : **Robin (recherche perso, régimes crypto)** | Garantit un canary permanent via Phase D. Ne dispense pas de chercher des utilisateurs externes (cf. critères de succès dans positionnement stratégique). |
| 2026-05-22 | **Refus** du pivot "meta-configurateur unifiant HMM / SSM / Transformer" | Brainstorm externe proposant un IR commun + compiler vers PyMC/Mamba/HuggingFace selon annotations utilisateur. **Rejeté** : (a) les sémantiques mathématiques ne mappent pas (HMM discret-Markov vs Transformer non-récurrent vs SSM continu) ; (b) "compile vers Mamba" serait du templating, pas un compilateur ; (c) ~2-3 ans de travail pour solo part-time ; (d) torpille le wedge HMM-niche qu'on vient de formaliser. **Ce qu'on garde** : le slogan "knowledge engineering for sequential processes" + l'idée d'un backend bayésien *dans le wedge HMM* (cf. Phase A.6). |
| 2026-05-22 | **Slogan adopté** : `hmm-studio` vend de l'**ingénierie de la connaissance pour processus séquentiels**, pas "un modèle HMM" | À utiliser dans README, doc site (Z.2), et toute communication externe. Aide à expliquer la valeur sans entrer dans la technique. |
| 2026-05-22 | **Distribution hybride** (ADR-0012) : core spécialiste HMM + surfaces d'intégration (Jupyter I.1, sklearn I.2, PyMC I.3) | A créé la Phase I et reframé Phase E (onglet web → notebook gallery). Slogan : *"the deepest HMM library in the Python scientific stack"*. |
| 2026-05-22 | **Rejet de l'expansion K·M / joint-state** pour GMM-NHMM (A.10) et Factorial (A.13) au profit de la décomposition 2-stage | L'expansion (Stratégie A) était sur-paramétrée sans contrainte de factorisation. Décidé *à l'implémentation*, documenté en spec pour ne pas relitiger. |
| 2026-05-26 | **A.6 Bayesian backend livré sans attendre le gating signal-externe** | Le pari distribution ADR-0012 (audience bayésienne académique via PyMC) a primé sur le gating original « ≥ 1 user externe d'abord ». Coût borné (~tenu), reste dans le wedge HMM. |
| 2026-06-02 | **Re-baseline du roadmap** (ce document) | La table d'état avait ~2 sem de retard. Re-synchronisée avec code/CHANGELOG/git. Confirme : le goulot n'est plus le code mais la **publication PyPI + l'adoption externe**. |

---

## Indicateurs de santé du projet

À monitorer en continu :

| Métrique | Cible | 2026-05-21 | 2026-05-22 (PM) | **2026-06-02** |
|---|---|---|---|---|
| Test coverage `src/hmm_core/` | ≥ 85% | 87% | 92% | ≥ 92% (maintenu) |
| Test count | croissant | 54 | 76 | **411** ↑↑ (31 fichiers) |
| Tests passing | 100% | 100% | 100% ✓ | 100% ✓ |
| Sub-projects livrés / planifiés | — | 1 / 4 | 3 + 1 validé / 5 | **~tous (A,A.1,A.5-A.10,A.13,B,B.10,C,D,E,I.1-I.3,V,Z) + post-v1.1** |
| Variants HMM livrés | — | 4 émissions | + NHMM | + GMM-NHMM, Factorial, Bayésien, supervisé/semi-sup |
| CI configurée | oui | non | oui | oui ✓ |
| Licence formalisée | oui | non | **MIT ✓** | MIT ✓ |
| Découplage backend (résilience hmmlearn) | oui | non | **HMMBackend ✓** | ✓ + Bayesian backend |
| **Publié sur PyPI** | oui (M5) | non | non | **🔴 NON — bloqué Trusted Publisher** |
| Utilisateurs externes réguliers | ≥ 3 à M3+6mois | 0 | 0 | **0** (premier user = Robin — *le vrai chantier ouvert*) |

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
- Licence : `LICENSE` (MIT, actée 2026-05-22)
- Citation académique : `CITATION.cff`
- Abstraction backend : `src/hmm_core/backends/` (livrée 2026-05-22)
- README utilisateur : see [Home](index.md)
- Dashboard HMM existant (validation D faite, swap futur) : `C:\Users\rdenis\VScode\Experiment.Crypto.2026S1.RobinDenis\src\cmex_crypto\viz\hmm_dashboard\`
- ADR de migration côté crypto (uncommitée pour relecture) : `C:\Users\rdenis\VScode\Experiment.Crypto.2026S1.RobinDenis\notes\decisions.md` (entrée 2026-05-21)

---

## Appendix — Variantes HMM hors-scope (gardées en mémoire)

> Cette section consigne les variantes HMM qu'on **n'implémente
> volontairement pas**, avec la justification du rejet. Elle existe pour
> éviter qu'une future session (ou une suggestion externe) revienne avec
> les mêmes propositions sans contexte. **Rejet ≠ ignorance** : on
> connaît, on a évalué, on a décidé que non.

| Variant | Description | Pourquoi rejet/defer | Conditions de réactivation |
|---|---|---|---|
| **Profile-HMM** (DEFERRED, voir A.12) | Modèle canonique bioinfo pour familles de séquences (HMMER, Pfam) | Marché bio dominé par HMMER ; pas notre wedge actuel | Signal bio explicite ou pivot business |
| **Pair-HMM** | Modèle d'alignement de paires de séquences | 100 % bioinfo. Sans A.12, sans intérêt. | Si A.12 réactivé, A.12.1 = Pair-HMM |
| **Coupled HMM** | Plusieurs chaînes qui interagissent (état d'une chaîne dépend des autres à t-1) | NHMM avec covariates exogènes (= sortie des autres chaînes) couvre les cas pratiques. Différent de Factorial qui suppose indépendance. | Cas d'usage où la dépendance entre chaînes est essentielle ET non capturable par covariates |
| **Topological HMM** | Extension recherche pour espaces topologiques complexes | Recherche exotique, aucun cas d'usage industriel, aucun bibliographic critical mass | Signal recherche académique très précis |
| **Auto-regressive HMM (AR-HMM)** | Observations dépendent de $x_{t-1}$ conditionnellement à l'état | Cas d'usage finance/signal réel. À reconsidérer si A.10/A.13 sur crypto montrent une limite résiduelle (autocorrélation non capturée) | Si fit GMM-NHMM ou Factorial sur crypto laisse une autocorrélation résiduelle visible |
| **Switching state-space model (Linear Gaussian SSM avec switching)** | Combine HMM et Kalman | Hors-scope HMM-land. Voir aussi décision tranchée 2026-05-22 contre meta-configurateur. | Pivot stratégique explicite vers SSM (non prévu) |
| **Variational HMM (deep learning)** | HMM avec encoder/decoder neural | Hors-scope (pivote vers deep learning). Stay in wedge. | Jamais sans pivot stratégique |
| **Continuous-time HMM (CTMC observed at irregular intervals)** | HMM en temps continu | Cas d'usage : événements rares (clicks, fraude). Niche, pas notre wedge | Signal industriel explicite (insurance, fraud detection) |

### Variantes **promues** ou **shippées** depuis l'audit initial

| Variant | Statut | Phase |
|---|---|---|
| Ergodic HMM | ✅ shippé | A |
| Left-Right (Bakis) HMM | ✅ shippé via `allowed_transitions` | A |
| Multinomial / Gaussian / GMM / Poisson HMM | ✅ shippé (4 émissions) | A |
| **IOHMM** (transitions covariate) | ✅ shippé | A.1 NHMM |
| **GMM-HMM statique** | ✅ shippé | A (émission GMM) |
| **GMM-NHMM** | 🚧 PLANNED | A.10 |
| **Markov Switching Model** | ✅ mathématiquement équivalent à HMM/NHMM (terminologie économétrique) | A + A.1 — pas de nouveau code, marketing dans le README |
| **Factorial NHMM** | 🚧 PLANNED (promu depuis appendix sur instinct Robin re: crypto multi-facteur) | A.13 |
| **Hierarchical HMM (HHMM)** | 📋 SPEC-ONLY (code gated) | A.11 |
| Profile-HMM | ⏸ DEFERRED | A.12 |

### Discipline appliquée

- Chaque rejet est **documenté** avec justification et conditions de
  réactivation
- Chaque promotion (Factorial dans cette session) est **explicite**, avec
  le raisonnement préservé
- Pas de "on verra" mou : soit on engage avec date, soit on défère avec
  conditions claires
