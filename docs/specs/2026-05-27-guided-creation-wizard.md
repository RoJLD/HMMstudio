# Guided HMM creation wizard — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis
**Status** : SPEC DRAFTED · prêt à planifier (1 phase, frontend-only)
**Effort estimé** : ~1.5-2 jours

> Emplacement : `docs/specs/` (convention réelle du projet, cf. les autres
> specs 2026-05-27). Divergence connue avec le `CLAUDE.md` local qui mentionne
> `docs/superpowers/specs/` — non tranchée ici.

---

## 1. Contexte et problème

Créer une topology aujourd'hui se fait dans l'**éditeur libre** (`TopologyPage`
+ `SidePanel` au-dessus d'un graphe reactflow) : on ajoute des états à la main,
on tire des arêtes, on règle émission/init/fit/priors dans le panneau latéral.
Puissant, mais **intimidant pour un nouveau venu** : tout est exposé d'un coup,
sans ordre ni explication, et il est facile de produire une spec qui ne
correspond pas aux données (mauvais `n_features` → erreur au fit).

On veut un **parcours guidé** qui amène un débutant de "rien" à "une topology
valide" en quelques étapes claires, qui *enseigne en configurant* (cohérent
avec l'Academy et les tooltips `?`), puis le dépose dans l'éditeur pour
peaufiner.

## 2. Goal

Un assistant **5 étapes** (« New guided model ») qui assemble une topology
valide à partir de décisions cadrées, **conscient des données chargées**
(pré-remplissage + garde-fous), réutilisant le moteur existant
(`yamlToTopology` + `loadTopology`), puis ouvre l'éditeur pré-rempli. Il
**coexiste** avec l'éditeur libre — il ne le remplace pas.

## 3. Design

### Décisions validées (2026-05-27)
- **Coexistence** : wizard → **handoff vers l'éditeur** (pas de remplacement,
  pas d'overlay). Bouton « ✨ New guided model » sur `TopologyPage`.
- **Nombre d'étapes** : **5** — une décision-concept par étape de modélisation
  (pédagogique), les réglages d'entraînement regroupés/par-défaut.
- **Conscience des données** : data-aware mais gracieux sans dataset.

### Les 5 étapes

| # | Étape | Décide | Data-aware | Défaut |
|---|---|---|---|---|
| 1 | **Emission** | type (gaussian/gmm/multinomial/poisson) + champs conditionnels (n_features, covariance, n_mix, n_symbols) | oui : préremplit `n_features = dataset.n_cols`, suggère le type, avertit en cas de mismatch | gaussian, n_features=1, full |
| 2 | **States** | `K` + noms d'états | — | K=3, noms `s0..s{K-1}` (rename optionnel) |
| 3 | **Transitions** | forme : **Ergodic** / **Left-right** / **Bakis** (+ « custom → éditeur ») | — | Ergodic |
| 4 | **Training** *(replié, par défaut)* | init (strategy+seed), fit (n_iter+tol), prior α | — | kmeans / 42 / 100 / 1e-4 / pas de prior |
| 5 | **Review** | récap en langage clair → **Finish** | montre « go to Fit » si dataset chargé | — |

**Détail data-aware (étape 1)** : `n_features` préremplie depuis
`useDatasetStore().current?.n_cols` (fiable). Suggestion de type : gaussian par
défaut ; si la métadonnée de dtype est exposée sur le preview de dataset (à
confirmer à l'impl — sinon fallback gaussian), proposer multinomial pour une
colonne entière unique et poisson pour des entiers ≥ 0. Avertissement non
bloquant si `n_features` ≠ nombre de colonnes du dataset.

**Détail transitions (étape 3)** : presets → `allowed_transitions` :
- *Ergodic* : pas de contrainte (tout autorisé) → `allowed_transitions` absent.
- *Left-right* : `s_i → s_i` et `s_i → s_{i+1}` seulement.
- *Bakis* : left-right + saut `s_i → s_{i+2}`.
- *Custom* : on garde Ergodic et on indique « dessine les arêtes dans
  l'éditeur après Finish ». (Le dessin arête-par-arête reste le job de
  l'éditeur, pas du wizard.)
Chaque preset affiche un mini-schéma.

**Enseignement intégré** : chaque étape réutilise la copie de `paramHelp` et
les liens « Learn more → » vers l'Academy (mêmes clés que les tooltips `?`).

### Architecture & handoff

- Nouvelle page `WizardPage` (route `/topology/new`), état local des 5 étapes
  (un index + un objet `WizardModel`). Bouton d'entrée sur `TopologyPage`.
- **Cœur pur et testable** : une fonction `buildTopologyYaml(model: WizardModel)
  : string` qui assemble la spec YAML (name, emission, n_states, state_names,
  allowed_transitions selon le preset, startprob, init, fit, prior). Pas d'état,
  pas d'I/O → unité la plus robuste.
- **Finish** : `yamlToTopology(buildTopologyYaml(model))` → `loadTopology(partial)`
  (le **chemin exact** utilisé par « Try in editor » des leçons et l'import YAML,
  cf. `LessonPage.tsx` / `TopologyPage.tsx`) → `navigate("/topology")`. Option
  secondaire « Finish & go to Fit » → `navigate("/fit")` si un dataset est chargé.
- **Validation par étape** : « Next » désactivé tant que l'étape n'est pas
  valide (ex. n_features ≥ 1, K ≥ 1, n_symbols ≥ 2 pour multinomial).

### Composants

- `pages/WizardPage.tsx` — orchestrateur (index d'étape, `WizardModel`, nav
  Back/Next, barre de progression `1—2—3—4—5`).
- `components/wizard/Step*.tsx` (5) — ou un seul switch interne ; au choix de
  l'impl, mais chaque étape reste un bloc focalisé.
- `lib/buildTopologyYaml.ts` — la fonction pure.
- Réutilise : `useTopologyStore.loadTopology`, `yamlToTopology`,
  `useDatasetStore`, `paramHelp` + `HelpTip`, les presets de transition.

## 4. Scope boundaries (ce qu'on ne fait PAS)

- **Pas de dessin d'arêtes** dans le wizard — presets de forme seulement ;
  l'édition fine reste dans l'éditeur.
- **Pas d'upload de données** dans le wizard — il lit le dataset déjà chargé ;
  l'upload reste sur la page Data.
- **Ne remplace pas** l'éditeur libre — coexistence (le bouton « Blank editor »
  reste).
- **Pas de nouveau modèle d'état** — réutilise `useTopologyStore` + le chemin
  `yamlToTopology`/`loadTopology`.
- **Pas de NHMM/covariables** dans le wizard v1 (covariables = page Fit). Le
  wizard produit une topology P(X) ; NHMM se configure ensuite.
- **Pas d'entrée de nav dédiée** en v1 — bouton sur `TopologyPage` (nav = futur
  éventuel).

## 5. Tests

Pas de runner JS (cf. specs précédents). Validation : `npm run build` (tsc
strict) vert + vérif manuelle (parcours des 5 étapes, presets, data-aware,
Finish → éditeur pré-rempli, « go to Fit »).

> ⚠️ Gap signalé : `buildTopologyYaml` est une fonction **pure** donc idéale
> pour un test unitaire (preset ergodic/left-right/bakis → bon
> `allowed_transitions` ; emission gmm → n_mix présent ; etc.). Si une infra de
> test JS (Vitest) est introduite, l'ajouter en priorité. Hors scope ici
> d'introduire le runner.

## 6. Définition de "done"

- [ ] Route `/topology/new` + `WizardPage` (5 étapes, progress, Back/Next, validation).
- [ ] Bouton « New guided model » sur `TopologyPage`.
- [ ] `buildTopologyYaml(model)` (fonction pure) couvrant émission, états,
      presets de transition, init/fit/prior.
- [ ] Data-aware étape 1 (préremplissage n_features + suggestion type +
      avertissement mismatch).
- [ ] `HelpTip`/paramHelp réutilisés sur les étapes.
- [ ] Finish → `loadTopology` → éditeur pré-rempli ; « Finish & go to Fit » si dataset.
- [ ] `npm run build` vert ; CHANGELOG `[Unreleased]` mis à jour.

## 7. Open questions (à résoudre pendant le plan)

1. **Métadonnée de dtype** sur le preview de dataset — exposée ou non ?
   Détermine la finesse de la suggestion de type (multinomial/poisson vs
   gaussian par défaut). À confirmer en lisant le type `DatasetPreview`.
2. **Forme exacte** des entrées `states`/`transitions` que `yamlToTopology`
   produit (positions des nœuds, ids) — déjà gérée par `yamlToTopology` ; le
   wizard n'a qu'à produire le YAML, mais confirmer qu'aucun champ requis ne
   manque pour un graphe valide.
3. **Noms d'états signifiants** : champ de rename inline en v1, ou auto
   `s0..s{K-1}` seulement (rename dans l'éditeur) ? Défaut proposé : rename
   inline optionnel léger.

## 8. Provenance

Demande utilisateur (2026-05-27) : « Lors de l'initialisation d'un HMM et sa
création, le faire en plusieurs étapes guidées ? 1—2—3—… ». Décisions de design
(coexistence wizard→éditeur ; 5 étapes après analyse du process ; data-aware
gracieux) validées le même jour (« Parfaitement allons y »).

## 9. Update 2026-05-27 — open questions resolved

L'utilisateur a délégué la résolution des 3 questions (« réponds à tes propres
questions, fais le plus complet »). Vérifié dans le code, tranché :

1. **dtype exposé : OUI.** `DatasetPreview` porte `dtypes: Record<string,string>`
   ET `head: Array<Record<string,unknown>>`. → Suggestion de type **complète**
   (pas seulement `n_features`) :
   - colonnes toutes flottantes → **gaussian**, `n_features = n_cols` ;
   - **une seule** colonne entière → **multinomial**, `n_symbols = max(head)+1`
     (≥ 2) ;
   - toutes colonnes entières et valeurs `head` ≥ 0 → **poisson**,
     `n_features = n_cols` ;
   - sinon → gaussian.
   Toujours surchargeable par l'utilisateur. Avertissement non bloquant si, une
   fois choisi, `n_features` (gaussian/gmm/poisson) ≠ `n_cols`, ou si multinomial
   et `n_cols ≠ 1`.
2. **Forme graphe : confirmée.** `yamlToTopology` génère `id`+`position`
   (layout grille `x=80+(i%4)*180, y=80+⌊i/4⌋*140`) pour chaque état et les `id`
   d'arêtes depuis les paires `allowed_transitions`. → Le wizard n'émet qu'un
   YAML topology standard ; tout le plumbing graphe est réutilisé. **Ergodic =
   omettre `allowed_transitions`.** Presets :
   - left-right : `[s_i,s_i]` ∀i + `[s_i,s_{i+1}]` ∀i<K-1 ;
   - bakis : left-right + `[s_i,s_{i+2}]` ∀i<K-2.
3. **Renommage d'états : OUI** (le plus complet). Champ inline optionnel à
   l'étape States, défaut `s0..s{K-1}`.

Ajout « complétude » retenu : à l'étape **Review**, afficher un aperçu YAML de
la topology assemblée (sortie de `buildTopologyYaml`) en plus du récap en
langage clair — transparence + apprentissage. Helpers purs séparés
(`allowedTransitionsForShape`, `suggestEmission`, `buildTopologyYaml`) pour la
testabilité et l'évolutivité.
