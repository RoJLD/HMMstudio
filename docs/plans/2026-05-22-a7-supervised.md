# Phase A.7 — Supervised training : plan d'implémentation et journal

**Date** : 2026-05-22
**Status** : SHIPPED (supervised) · A.7.1 punted (semi-supervised)
**Spec source** : `docs/roadmap.md` § "Phase A.7 — Modes supervisé et semi-supervisé"

> Ce fichier est volontairement séparé de la roadmap pour éviter les
> conflits d'édition avec la session B (UI web) qui tourne en parallèle.
> Sera fusionné dans la roadmap lors de la prochaine session séquentielle.

## Ce qui a été livré

### Code

- **`src/hmm_core/backends/_protocol.py`** : ajout de la méthode
  `HMMBackend.fit_supervised(topology, X, states, *, seed, lengths, mask)`
  retournant un `BackendFitResult`. Documentée avec contrat strict :
  - `states` shape `(T,)` int dans `[0, K)`
  - Le backend DOIT lever `ValueError` si une transition observée
    viole le `mask`.
- **`src/hmm_core/backends/hmmlearn_backend.py`** : implémentation
  `HmmlearnBackend.fit_supervised()` + 4 helpers privés numpy purs :
  - `_iter_within_sequence(T, lengths)` — itère les paires `(t, t+1)`
    sans franchir les bornes de séquence.
  - `_supervised_transmat(states, K, mask, lengths)` — compte les
    transitions, vérifie la compatibilité avec le mask, applique
    `_apply_mask` + lissage Laplace ε=1e-10.
  - `_supervised_startprob(states, K, lengths)` — distribution
    empirique des premiers états de chaque séquence.
  - `_supervised_emission_mle(topology, X, states, K)` — MLE
    closed-form par état pour gaussian / multinomial / poisson.
    GMM lève `NotImplementedError("planned for A.7.1")`.
- **`src/hmm_core/fit/__init__.py`** : `fit()` accepte
  `states: np.ndarray | None = None`. Quand fourni :
  - validation shape + valeurs
  - détection `NaN` → `NotImplementedError("A.7.1")` explicite
  - dispatch vers `backend.fit_supervised(...)`
  - BIC/AIC calculés sur le `log_likelihood` du fit closed-form

### Tests : 13 nouveaux dans `tests/test_supervised.py`

| Test | Vérifie |
|---|---|
| `test_supervised_converges_in_one_pass_gaussian` | `n_iter_actual == 1`, `converged is True` |
| `test_supervised_transmat_matches_count_matrix` | transmat = comptage normalisé empirique |
| `test_supervised_respects_topology_mask_when_compatible` | edges interdits restent à 0 |
| `test_supervised_raises_when_labels_violate_mask` | erreur explicite si labels incompatibles avec mask |
| `test_supervised_emission_means_recovered` | μ_k retrouvés sur données bien séparées |
| `test_supervised_rejects_states_with_wrong_length` | validation shape |
| `test_supervised_rejects_states_out_of_range` | validation valeurs `[0, K)` |
| `test_semisupervised_not_yet_implemented` | NaN → `NotImplementedError("A.7.1")` |
| `test_supervised_multinomial_emissionprob_matches_counts` | MLE multinomial = comptage |
| `test_supervised_poisson_lambdas_match_per_state_means` | MLE poisson = moyenne par état |
| `test_hmmlearn_backend_exposes_fit_supervised` | méthode disponible |
| `test_backend_fit_supervised_returns_BackendFitResult` | type de retour conforme au protocole |
| `test_supervised_with_lengths_no_cross_sequence_transition` | les bornes de séquences sont respectées |

### Métriques

- **Tests** : 76 → 89 (+13). 100 % passent.
- **Coverage** : 92 % → 89 % (la dette vient du chemin GMM NotImplemented
  + quelques branches de validation que je n'ai pas tous testées).
  À reprendre en A.7.1 ou en cleanup ad hoc.

## Ce qui N'A PAS été livré (A.7.1, à planifier séparément)

### Semi-supervised mode

Quand `states` contient des `NaN` (positions inconnues), on aimerait :
- E-step de Baum-Welch contraint aux positions labelées (gamma forcé
  one-hot là où l'état est connu).
- OU Viterbi training avec contrainte dure (Viterbi qui respecte les
  positions labelées).

**Pourquoi pas dans cette session** : nécessite soit un hook dans
l'E-step d'hmmlearn (qu'on s'est interdits via l'abstraction backend),
soit notre propre Viterbi/forward-backward implémenté en numpy. Pas
trivial sans dégrader la qualité numérique. Méritant sa propre session.

**Aujourd'hui** : la signature accepte des `NaN` mais lève
`NotImplementedError` avec un message clair pointant vers A.7.1.

### GMM supervised

Idem : un GMM supervisé nécessite de fitter `n_mix` sous-composantes par
état (problème non-supervisé local par état). Implémentable via
`sklearn.mixture.GaussianMixture` par état mais avec des subtilités sur
les types de covariance. Punted vers A.7.1.

**Aujourd'hui** : type GMM lève `NotImplementedError` explicite.

### CLI `--labels`

Le flag CLI `hmm-fit run --labels states.csv` n'est pas implémenté.
Mineure, à ajouter quand on aura un cas d'usage concret. L'API Python
suffit pour Robin et pour la Phase D (dashboard crypto).

### Section README "Training modes"

Pas écrite — pour éviter les conflits avec la session B qui touche
peut-être au README. À ajouter dans une session séquentielle.

## Coordination avec la session B (en parallèle)

- Surface A.7 : strictement dans `src/hmm_core/` + `tests/test_supervised.py`.
- Surface B : `src/hmm_studio/server/`, `tests/studio/`,
  `docs/decisions/0002-b-stack-decisions.md`,
  `docs/plans/2026-05-22-b1-backend-skeleton.md`.
- **API publique inchangée** côté B : le paramètre `states=None` par
  défaut garantit que toute consommation existante de `fit(topology, X)`
  continue de fonctionner identiquement.

## Prochaines étapes (par ordre de priorité, sous réserve de re-décision)

1. **Mettre à jour la roadmap** (`docs/roadmap.md` § A.7) — marquer
   "SHIPPED (supervised)", garder A.7.1 comme bloc séparé. À faire en
   session séquentielle après B (ou la prochaine fois que personne
   d'autre n'édite la roadmap).
2. **A.7.1** : Semi-supervised + GMM supervised. ~1 semaine de travail
   estimé. Dépend de : avoir un cas d'usage réel qui le demande
   (sinon ne pas le construire — cf. discipline anti-scope-creep).
3. **CLI `--labels`** : 1-2 heures quand on a un dataset d'exemple
   supervisé canonique.
