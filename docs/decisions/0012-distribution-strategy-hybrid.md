# ADR-0012 — Distribution strategy : HMM specialist + integration surface

**Date** : 2026-05-22
**Status** : ACCEPTED
**Auteur** : Robin Denis (avec architecte-CEO framing)

---

## Contexte

Au cours du développement de `hmm-studio`, on a empilé : moteur HMM
(A, A.1, A.10, A.13), abstraction backend (A.5), supervised training (A.7),
suite de validation scientifique (V), data warehouse (B.10), prep layer
(B.11), éditeur visuel de topology (B.4), academy (E, planifié), comparison
layer (B.12, planifié).

Le pattern observé : on glisse progressivement vers la forme d'une
**plateforme de recherche généraliste**. Robin a explicitement identifié ce
drift (2026-05-22 PM) et posé la question stratégique : *est-ce qu'on
grandit (devenir une plateforme générale), reste spécifique HMM (niche
profonde), ou hybride (spécifique HMM + intégration avec plateformes
matures) ?*

### Paysage compétitif honnête

Si on tente de grandir vers une plateforme généraliste, on entre en
compétition frontale avec :
- **JupyterLab** — 10+ ans, écosystème Python entier
- **KNIME / Orange** — 15+ ans, drag-drop workflows visuels, mature
- **Hex / Deepnote / Mode** — cloud notebooks + warehouse, commercial avec
  levées récentes
- **Streamlit / Gradio** — apps ML rapides, dominants

Pour un solo developer part-time, c'est inatteignable. Même avec
financement, c'est 5-10 ans avec une équipe de 10+.

### Précédents stratégiques (qui survivent)

- **Stan** — langage probabilistique core, expose PyStan / CmdStan / brms /
  rstanarm comme surfaces de distribution
- **HMMER** — moteur profile-HMM core, intègre Pfam / BLAST en surface
- **scikit-learn** — fit/transform API core, devenu foundation pour
  pandas/lightgbm/xgboost/tensorflow Estimators
- **NumPy** — n-dim array core, toute la stack scientifique dépend de lui

Le pattern commun : **rester profond sur son wedge ET exposer une surface
d'intégration propre vers les plateformes matures qui distribuent déjà**.

---

## Décision

**Option 3 — Stratégie hybride** : hmm-studio reste spécialiste HMM dans
son core, et investit en parallèle dans des **surfaces de distribution**
vers des plateformes matures.

### Trois surfaces de distribution prioritaires

| Surface | Effort | Gain | Quand |
|---|---|---|---|
| **I.1 Jupyter-first** | ~2-3 j | Énorme — chaque chercheur utilise notebook | Démarrer immédiatement |
| **I.2 scikit-learn-compatible API** | ~3-5 j | Énorme — entre dans pipelines existants | Court terme |
| **I.3 PyMC / NumPyro bridge** | Couplé A.6 (~1-2 sem) | Audience bayésienne académique | Gated sur A.6 |

### Phrase de positionnement officielle (après cette décision)

> *"hmm-studio is the deepest HMM library in the Python scientific stack —
> pip-installable, sklearn-compatible, Jupyter-native, with optional
> standalone GUI for non-Python users. We don't replace your research
> environment ; we slot in as the HMM specialist."*

### Test de validation stratégique (à appliquer aux propositions futures)

Pour toute feature proposée, on demande :

> **Le matin où un chercheur en éco découvre hmm-studio, comment
> l'utilise-t-il ?**
>
> ✅ Bon : `pip install hmm-studio` → ouvre un notebook → est productif en 5 min
>
> ❌ Mauvais : il doit installer une app web séparée et apprendre un nouvel
> environnement

---

## Alternatives considérées

### Option 1 — Grandir (plateforme généraliste)

**Rejeté** : suicidaire pour un solo dev part-time. Concurrents trop matures
et bien financés. Aucune chance de rattraper en feature parity. Risque de
diluer le wedge HMM en construisant un sous-pandas / sous-KNIME.

### Option 2 — Rester strictement HMM-niche

**Rejeté comme stratégie d'ambition principale** (mais conservé comme
fallback safe). Plafond de croissance dur, isolement des workflows
utilisateurs, pas d'effets réseau, croissance lente. Acceptable si on
abandonne l'ambition produit, pas si on veut une trajectoire.

### Option 3 — Hybride (RETENU)

Préserve le moat (profondeur HMM), s'inscrit dans l'écosystème (distribution
via plateformes matures), réaliste en solo, survie démontrée par
précédents (Stan, HMMER, sklearn, NumPy).

---

## Conséquences

### Sur les phases en cours

| Phase | Avant la décision | Après la décision |
|---|---|---|
| **B web UI** | Le produit principal visible | **De-emphasis stratégique**. Maintenu pour utilisateurs non-Python (industriels) mais cesse d'être le centre d'investissement. |
| **B.10 warehouse** | Centerpiece de l'app web | **De-emphasis**. Devient *un input source parmi d'autres*. Notebook = nouveau centerpiece. |
| **B.11 prep** | OK comme spec | **Reste tel quel** — utile en notebook autant qu'en web. Engine general + recipes HMM-canonical reste le bon design. |
| **E Academy** | Onglet web standalone | **Reframe** : la **notebook gallery officielle devient l'academy**. Plus naturel pour chercheurs, plus de distribution. Le tab web reste optionnel. |
| **B.12 comparison** (proposé) | Layer interne | OK comme spec, consommé principalement depuis notebooks. |
| **C visualisations avancées** | Pour la web UI | **De-emphasis**. Migration partielle vers visualisations Jupyter rich displays. |
| **NEW Phase I — Integrations** | n'existait pas | **Phase prioritaire neuve** : I.1 (Jupyter), I.2 (sklearn), I.3 (PyMC bridge). |

### Sur la roadmap

- Nouvelle Phase I ajoutée avec 3 sous-phases livrables incrémentaux
- Le séquencement est rééquilibré : I.1 et I.2 deviennent **prioritaires
  avant E** dans la mesure où ils mangent une partie de la valeur d'E
  (la notebook gallery)
- B web UI continue d'avoir maintenance + bug fixes, mais pas de nouveau
  gros chantier majeur (B.4.x topology editor reste l'invest principal
  côté web)

### Sur la mémoire stratégique

Nouveau fichier mémoire `hmm_studio_distribution_strategy.md` qui :
- Documente la phrase de positionnement officielle
- Capture le test de validation (le scénario chercheur)
- Liste les surfaces de distribution et leur ordre
- Garde-fou anti-glissement vers "plateforme généraliste"

### Sur la communication externe

- README : mettre en avant l'install pip + notebook quickstart AVANT le web
- Doc site (Z.2) : doc Python notebook = first-class, web GUI = section secondaire
- Tweets / blog posts / academic outreach : citer "the HMM specialist in
  your stack" plutôt que "an HMM modeling platform"

### Ce qui NE change PAS

- Le wedge HMM reste le wedge (constrained Baum-Welch, NHMM, GMM-NHMM,
  Factorial restent notre profondeur unique)
- La discipline scope reste (pas d'ARIMA/GARCH/Prophet, pas de meta-config,
  pas de DAG editor visuel généraliste)
- La rigueur validation reste (V suite reste notre crédibilité scientifique)
- Tout le code déjà livré reste valuable et utilisé

---

## Plan d'implémentation

### I.1 Jupyter rich displays + notebook gallery

**Surface** :
- `Topology.__repr_html__()` — graphe interactif inline
- `FittedModel._repr_html_()` — heatmap transmat + Viterbi
- `NHMMFittedModel._repr_html_()` — A(t) animé inline (export D3 HTML)
- `Pipeline._repr_html_()` — chaîne des steps avec preview
- Notebook gallery sur GitHub/binder (5-10 notebooks canoniques)
- Magic commands `%load_ext hmm_studio` (optionnel, à ré-évaluer si besoin)

**Effort** : ~2-3 jours.

### I.2 scikit-learn compatible API

**Surface** :
- `HMMClassifier(n_states, topology, ...)` — implements `BaseEstimator`,
  `ClassifierMixin`, `fit(X, y=None)`, `predict(X)`, `score(X, y)`
- `HMMRegressor` — pour cas où on prédit l'observation suivante
- `get_params()` / `set_params()` pour grid search
- Compatible avec `Pipeline`, `cross_val_score`, `GridSearchCV`
- Documentation avec exemples d'intégration sklearn

**Effort** : ~3-5 jours.

### I.3 PyMC / NumPyro bridge (gated sur A.6)

**Surface** :
- `hmm_studio.pymc_bridge.HMMTopologyPyMC.from_yaml(path)`
- Génère le code PyMC équivalent à un topology YAML
- Compatible avec `pm.sample()` standard
- Convertit `InferenceData` arviz → nos `FittedModel`

**Effort** : ~1-2 semaines, gated sur A.6 (Bayesian backend).

### I.4+ deferred (à gater sur signal)

- MLflow model flavor
- VS Code extension pour YAML topology editing
- Streamlit components
- Hugging Face hub publishing (probablement N/A pour HMM)
- KNIME nodes (probablement N/A)

---

## Notes pour les futures sessions

- **Pas de revisite de cette décision avant M+6 mois minimum**, sauf signal
  externe majeur (ex : un VC veut financer une plateforme complète)
- **Tout nouveau spec doit passer le test stratégique** : "scénario
  chercheur découvrant hmm-studio à 8h du matin"
- **Si tentation de centrer sur la web UI revient** : relire cet ADR
- **Si tentation de devenir une plateforme généraliste** (DAG editor,
  warehouse complet, model garden) : refuser fermement, citer cet ADR

---

## Références

- Brainstorm strategy 2026-05-22 PM (Robin + Claude Opus 4.7)
- Précédents : Stan (PyStan/CmdStan/brms), scikit-learn API, HMMER + Pfam
- Phase I spec : `docs/specs/2026-05-22-phase-i-integrations.md` (à créer
  quand on commence l'implémentation de I.1 / I.2)
