# Phase V — Scientific validation suite : spec

**Date** : 2026-05-22
**Auteur** : Robin Denis (avec architecte-CEO framing)
**Status** : SPEC DRAFTED · prêt à implémenter
**Effort estimé** : 3-5 jours
**Prérequis** : aucun (peut démarrer immédiatement)

> Document de spec. Pour le contexte stratégique et la priorité, voir
> [docs/roadmap.md § Phase V](../roadmap.md).

---

## 1. Contexte et motivation

Les 131 tests actuels du projet sont des **tests de correction du code**.
Ils vérifient que :
- L'API publique a la bonne signature
- Les contrats d'interface sont respectés (mask, validation, etc.)
- Les régressions ne reviennent pas
- Les edge cases (état vide, séquence courte, etc.) ne crashent pas

Ils ne vérifient **pas** que les sorties numériques sont **correctes** au
sens scientifique. Un test qui dit "le transmat respecte le mask" est
satisfait par un transmat **complètement faux** tant qu'il respecte le
mask. Un test qui dit "le supervisé converge en une passe" ne dit rien
sur la qualité du fit.

**Pour un outil destiné à la recherche académique et à l'enseignement,
c'est un trou inacceptable.** Quand un reviewer demande à un chercheur
"comment savez-vous que votre Baum-Welch est correctement implémenté ?",
la réponse doit être documentée et reproductible.

## 2. Périmètre

### Inclus
- 4 couches de validation (V.1 → V.4 ci-dessous)
- ~18-20 tests scientifiques, séparés des unit tests
- Documentation `validation/README.md` listant chaque test avec sa source
  canonique et sa tolérance
- Badge "Validated against canonical references" sur le README principal
- Fixtures pour les jeux de données canoniques

### Exclus (hors-scope explicite)
- Tests d'inférence causale, contrefactuels, robustesse adversariale →
  hors-périmètre HMM
- Benchmarks de performance (vitesse de fit, mémoire) → utile mais c'est
  une autre suite
- Tests sur le frontend (couvert par tests Playwright dans Phase B)
- Comparaison avec Stan / PyMC → reportée en Phase A.6 (Bayesian backend)

## 3. Architecture de la suite

### Layout fichiers

```
hmm_studio/
├── validation/                    # NOUVEAU répertoire
│   ├── README.md                  # liste tests + sources + tolérances
│   ├── conftest.py                # markers, fixtures partagées
│   ├── fixtures/                  # données canoniques
│   │   ├── russell_norvig_umbrella.yaml
│   │   ├── russell_norvig_umbrella_obs.csv
│   │   ├── durbin_dishonest_casino.yaml
│   │   ├── durbin_dishonest_casino_obs.csv
│   │   ├── rabiner_1989_weather.yaml
│   │   └── eisner_ice_cream.yaml
│   ├── test_v1_cross_check_hmmlearn.py
│   ├── test_v2_recovery_synthetic.py
│   ├── test_v3_textbook_canonical.py
│   └── test_v4_numerical_stability.py
└── tests/                         # inchangé, dev unit tests
```

### Exécution

- Suite séparée : pas dans la CI par défaut (trop lente)
- Markers pytest dédiés : `@pytest.mark.validation`, `@pytest.mark.slow`
- Lancée :
  - À chaque release majeure (v0.3, v0.4, ...)
  - À chaque changement de version d'`hmmlearn` (bump dependency)
  - À l'ajout d'un nouveau backend (PomegranateBackend, BayesianHMMBackend)
  - Optionnellement nightly via GitHub Actions cron

### Commandes

```bash
# Toute la suite validation
pytest validation/ -m validation

# Une couche en particulier
pytest validation/test_v3_textbook_canonical.py

# Avec rapport détaillé (numbers, deviations)
pytest validation/ -m validation -v --tb=short
```

## 4. Détail des 4 couches

### V.1 — Cross-check vs `hmmlearn` baseline (sanity layer)

**Objectif** : sur une topologie ergodique sans contraintes structurelles,
notre `fit()` doit produire **strictement les mêmes paramètres**
qu'`hmmlearn` direct (mêmes seed, mêmes init params). Si V.1 échoue, on
a un bug dans le glue code, pas dans la math.

**Tests** (4) :

| # | Topologie | Émission | Seed | Tolérance |
|---|---|---|---|---|
| V.1.1 | 3-state ergodique | Gaussian (diag) | 42 | 1e-12 sur transmat, means, covars |
| V.1.2 | 3-state ergodique | GMM (2 mix, diag) | 42 | 1e-10 sur transmat, means, covars, weights |
| V.1.3 | 4-symbol 2-state ergodique | Multinomial | 42 | 1e-12 sur transmat, emissionprob |
| V.1.4 | 2-state ergodique | Poisson | 42 | 1e-12 sur transmat, lambdas |

**Méthode** :
```python
# Référence
ref_model = hmmlearn.hmm.GaussianHMM(...).fit(X)

# Nous
ours = fit(topology_ergodic, X, seed=42)

# Asserts
np.testing.assert_allclose(ours.model.transmat_, ref_model.transmat_, atol=1e-12)
np.testing.assert_allclose(ours.model.means_, ref_model.means_, atol=1e-12)
```

**Tolérance justification** : sur topologie ergodique sans mask, notre
code délègue intégralement à `hmmlearn`. La seule source de différence
serait un bug d'init ou d'ordre d'opérations → 1e-12 est conservateur.

### V.2 — Recovery sur synthétique (statistical correctness)

**Objectif** : générer des observations depuis un HMM avec paramètres
connus, fitter avec notre outil, vérifier que l'estimateur converge vers
les vrais paramètres à mesure que N croît. C'est le test de **correction
statistique** : la loi des grands nombres doit s'appliquer.

**Tests** (5-6) :

| # | Vrai modèle | N obs | Tolérance |
|---|---|---|---|
| V.2.1 | Gaussian 3-state diag, K=3, D=2 | 10000 | ‖μ̂ - μ‖ < 0.1, ‖Σ̂ - Σ‖_F < 0.2 |
| V.2.2 | Gaussian left-right 4-state full | 5000 | identique + transmat KL div < 0.05 |
| V.2.3 | Multinomial 3-state, 5 symbols | 5000 | ‖p̂ - p‖_1 < 0.05 per state |
| V.2.4 | Poisson 2-state, D=1 | 3000 | |λ̂ - λ| / λ < 5% per state |
| V.2.5 | GMM 2-state 3-mix diag | 5000 | tolérance plus lâche (identifiabilité fragile) |
| V.2.6 | NHMM 3-state, 2 covariates (régression) | 5000 | β̂ recovery test |

**Méthode** :
```python
# Vrai modèle
true_topo = Topology(...)
true_params = {"means_": ..., "covars_": ..., "transmat_": ..., ...}
X = simulate_from_hmm(true_topo, true_params, n_obs=10000, seed=0)

# Fit
result = fit(true_topo, X, seed=42)

# Mesure de l'écart
assert recover_metric(result.model, true_params) < threshold
```

**Tolérance justification** : déduite analytiquement de la variance MLE
asymptotique (σ²/N) pour les moyennes ; empirique pour les autres
paramètres avec marge de sécurité ×2.

**Note importante** : permutation d'états. L'identifiabilité du HMM est
modulo permutation des états. La métrique de recovery doit donc utiliser
l'**assignment optimal de Hungarian** (scipy.optimize.linear_sum_assignment)
pour matcher les états estimés aux vrais avant comparaison.

### V.3 — Textbook problems (analytical correctness)

**Objectif** : reproduire des résultats publiés et largement
référencés. Quand un academic demande "votre Viterbi est-il correct ?",
on lui pointe vers ces tests.

**Tests** (4-6) :

#### V.3.1 — Russell & Norvig umbrella (AIMA, ch. 14)

- 2 états : rain, sun
- 2 observations : umbrella, no_umbrella
- Transition : P(rain | rain) = 0.7, P(sun | sun) = 0.7
- Émission : P(umbrella | rain) = 0.9, P(umbrella | sun) = 0.2
- Séquence : [umbrella, umbrella, no_umbrella, umbrella, umbrella]
- **Référence** : table 14.6 du livre. Forward at t=1 : `<0.818, 0.182>`,
  Forward at t=2 : `<0.883, 0.117>`, etc.
- **Notre test** : charger ce YAML + données fixtures, faire un
  `predict_proba`, vérifier chaque ligne à 1e-4 près des tables AIMA.

#### V.3.2 — Durbin dishonest casino

- 2 états : fair, loaded
- 6 observations (faces de dé)
- Émissions fixées : fair = uniforme(1/6), loaded = [0.1]*5 + [0.5]
- Transitions : P(stay) = 0.95 (fair), 0.9 (loaded)
- **Référence** : Durbin et al. "Biological Sequence Analysis", chap. 3
  exemple p. 54-58. Inclut une séquence canonique de 300 obs avec leur
  Viterbi attendu.
- **Notre test** : Viterbi de la séquence canonique doit matcher la
  référence à 100 % (output discret).

#### V.3.3 — Rabiner 1989 weather example

- L'exemple canonique de l'article fondateur de Rabiner
- 3 états (sunny, rainy, foggy)
- Émissions et transitions tabulées
- **Notre test** : reproduire les calculs forward/backward de la table II
  de Rabiner 1989 à 1e-4 près.

#### V.3.4 — Eisner ice cream HMM

- 2 états (hot, cold weather), observations = #ice creams eaten (1/2/3)
- Données canoniques : `333112212`
- **Référence** : exemples pédagogiques Eisner (Johns Hopkins), tableaux
  forward dans ses slides + livre.

#### V.3.5 — Profile HMM minimal (bioinfo)

- Profile HMM gauche-droite 3 états insert/delete/match
- Données : alignement minimal canonique
- **Test optionnel**, demande effort d'adaptation (HMMER format ≠ notre YAML)

### V.4 — Numerical stability stress (robustness)

**Objectif** : casser les cas pathologiques avant que l'utilisateur ne le
fasse.

**Tests** (4-5) :

| # | Stress | Critère |
|---|---|---|
| V.4.1 | Séquence très longue (T=100000) | Pas d'underflow, log-likelihood fini, fit termine en < 60s |
| V.4.2 | Covariance quasi-singulière (cond > 1e10) | Régularisation kick in, pas de SVD failure |
| V.4.3 | État rare (visité 2 fois sur 10000) | MLE supervised ne crash pas (smoothing tient) |
| V.4.4 | K élevé (K=50) avec left-right strict | Fit termine, mask respecté, log-lik fini |
| V.4.5 | Probabilités quasi-nulles (1e-30) dans transmat init | Forward stable en log-space |

**Méthode** : chaque test génère synthétiquement le cas stress puis lance
`fit()` avec un `pytest.warns(None)` (zéro warning attendu) et assert
sur la finitude du log-likelihood.

## 5. Documentation et présentation

### `validation/README.md`

Doit contenir, par test :
- ID (V.x.y)
- Source canonique citée précisément (titre + chapitre + page si livre,
  DOI si article)
- Tolérance numérique avec justification
- Commande pour le lancer en isolation
- Résultat attendu (où c'est applicable, valeurs précises)

### Badge README principal

```markdown
[![Scientific validation](https://img.shields.io/badge/validation-Russell%20%26%20Norvig%20%7C%20Durbin%20%7C%20Rabiner-blue)](validation/README.md)
```

### ADR à créer

`docs/decisions/0006-scientific-validation-suite.md` :
- Pourquoi suite séparée des unit tests ?
- Pourquoi ces 4 couches et pas d'autres ?
- Pourquoi ces sources canoniques précises ?
- Comment ajouter une nouvelle couche / un nouveau test ?

## 6. Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Tolérance V.2 trop stricte → tests flakies | Moyenne | Marker `@pytest.mark.flaky(reruns=2)` + documenter la variance attendue |
| Coût compute des recovery tests | Moyenne | Marker `@slow`, nightly seulement, pas dans le `pytest` par défaut |
| Discrépance V.1 vs hmmlearn sur cas extrêmes | Faible | C'est précisément ce qu'on veut détecter ; si ça se produit, ouvrir issue dédiée |
| Sources textbook indisponibles / mal référencées | Faible | Préférer les livres open-access (Durbin chapitre est en ligne ; AIMA tables aussi) |
| V.2 dépend d'une primitive de simulation pas encore livrée | Moyenne | Si `simulate_from_hmm` n'existe pas, l'écrire d'abord (~2h) — utile en soi |

## 7. Définition de "done" pour V

- [ ] `validation/` créé avec les 4 fichiers `test_v1` ... `test_v4`
- [ ] ~18-20 tests passent avec tolérances documentées
- [ ] `validation/README.md` complet
- [ ] Fixtures pour V.3 (yaml + csv) dans `validation/fixtures/`
- [ ] Badge ajouté au README principal
- [ ] ADR-0006 rédigée
- [ ] Une mention dans le slogan / pitch : "Validated against textbook references"

## 8. Successeurs probables (hors-scope V)

Une fois V livré, deux extensions naturelles, à gater sur usage :
- **V.5 Performance benchmarks** : suite séparée mesurant temps de fit
  vs taille séquence, K, type d'émission. Utile si on veut faire des
  promesses de SLA / si quelqu'un benchmarke contre nous.
- **V.6 Comparaison cross-backend** : quand BayesianHMMBackend (A.6) ship,
  vérifier que MAP du Bayésien converge vers MLE quand le prior est plat.

Ces deux sont reportés à plus tard ; pas de pré-engagement.
