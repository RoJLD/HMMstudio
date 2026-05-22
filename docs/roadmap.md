# `hmm-studio` — Roadmap complète

**Date de création** : 2026-05-21
**Auteur** : Robin Denis
**Dernière mise à jour** : 2026-05-22 (session "architecte-CEO" : licence MIT
actée, abstraction backend livrée, positionnement stratégique formalisé)

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

```
Phase    Sous-projet                       Statut         Dépend de   Échéance estimée
─────────────────────────────────────────────────────────────────────────────────────────
   A     hmm-core (Python engine + CLI)    SHIPPED v0.1   —           livré 2026-05-21
   A.next Polish (GMM tied bug, coverage,  SHIPPED        A           livré 2026-05-22
         lengths param)
   A.1   NHMM dans le core (fit_nhmm)      SHIPPED v0.2   A           livré 2026-05-22
   A.5   HMMBackend abstraction layer      SHIPPED        A           livré 2026-05-22
         (decouple from hmmlearn)
   A.7   Modes supervisé + semi-supervisé  PLANNED        A.5         ~1 semaine
         (fit avec états labelés)                                     prioritaire avant A.6
   A.6   BayesianHMMBackend (PyMC/NumPyro) OPTION         A.5, B,     conditionnel
         — option défendue, pas engagement                signal ext. (voir gating)
   D     Migration dashboard crypto        VALIDATED      A           regression test
                                           (regression               passe, ADR ajoutée
                                           + ADR, pas               dans crypto repo,
                                           swap)                     non commitée
   Z.1   GitHub Actions CI + pre-commit    SHIPPED        —           livré 2026-05-22
   Z.5   Licence MIT + CITATION.cff        SHIPPED        —           livré 2026-05-22
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

**Status** : PLANNED · prioritaire avant A.6
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

## Phase A.6 — Backend bayésien (PyMC / NumPyro) — *option défendue, pas engagement*

**Status** : NOT STARTED · candidat post-B, et **après A.7** dans tous les cas
**Dépend de** : A.5 (abstraction backend, livrée), A.7 (modes d'entraînement),
B MVP shipped + signal externe

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
6. **Doc site** : mkdocs vs docusaurus vs custom. À trancher en Z.2.

### Décisions tranchées (historique)

| Date | Décision | Notes |
|---|---|---|
| 2026-05-22 | Licence : **MIT** | `LICENSE` + `CITATION.cff` à la racine. Ré-licenciement futur possible (les versions passées restent MIT, mais c'est acceptable). |
| 2026-05-22 | Abstraction backend : **HMMBackend Protocol** + registry, hmmlearn comme backend par défaut | Décou­ple `hmm-core` de hmmlearn. Voir A.5. |
| 2026-05-22 | Premier utilisateur officiel : **Robin (recherche perso, régimes crypto)** | Garantit un canary permanent via Phase D. Ne dispense pas de chercher des utilisateurs externes (cf. critères de succès dans positionnement stratégique). |
| 2026-05-22 | **Refus** du pivot "meta-configurateur unifiant HMM / SSM / Transformer" | Brainstorm externe proposant un IR commun + compiler vers PyMC/Mamba/HuggingFace selon annotations utilisateur. **Rejeté** : (a) les sémantiques mathématiques ne mappent pas (HMM discret-Markov vs Transformer non-récurrent vs SSM continu) ; (b) "compile vers Mamba" serait du templating, pas un compilateur ; (c) ~2-3 ans de travail pour solo part-time ; (d) torpille le wedge HMM-niche qu'on vient de formaliser. **Ce qu'on garde** : le slogan "knowledge engineering for sequential processes" + l'idée d'un backend bayésien *dans le wedge HMM* (cf. Phase A.6). |
| 2026-05-22 | **Slogan adopté** : `hmm-studio` vend de l'**ingénierie de la connaissance pour processus séquentiels**, pas "un modèle HMM" | À utiliser dans README, doc site (Z.2), et toute communication externe. Aide à expliquer la valeur sans entrer dans la technique. |

---

## Indicateurs de santé du projet

À monitorer en continu :

| Métrique | Cible | 2026-05-21 | 2026-05-22 | 2026-05-22 (PM) |
|---|---|---|---|---|
| Test coverage `src/hmm_core/` | ≥ 85% | 87% | 92% ↑ | 92% (maintenu post-backend) |
| Test count | croissant | 54 | 66 ↑ | 76 ↑ |
| Tests passing | 100% | 100% | 100% ✓ | 100% ✓ |
| Open dette (items du final review) | ≤ 5 | 3 | 0 ✓ | 0 ✓ |
| Sub-projects livrés / planifiés | — | 1 / 4 | 2 + 1 validé / 5 | 3 + 1 validé / 5 (A.5) |
| Specs draftées (B, C) | — | 0 | 2 ✓ | 2 ✓ |
| CI configurée | oui | non | oui (en attente de remote) | oui |
| Licence formalisée | oui | non | non | **MIT ✓** |
| Découplage backend (résilience hmmlearn) | oui | non | non | **HMMBackend ✓** |
| Utilisateurs externes réguliers | ≥ 3 à M3+6mois | 0 | 0 | 0 (premier user = Robin, à monitorer) |

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
