# ADR-0004 : Supervised training (Phase A.7)

**Date** : 2026-05-22
**Status** : Accepted
**Auteurs** : session parallèle + documentation par la session principale

## Contexte

La promesse originale de `hmm-core` (sous-projet A) est l'**unsupervised**
training : on observe `X` mais pas la séquence d'états sous-jacents, et
Baum-Welch (EM) estime les paramètres conjointement avec les états.

Une classe d'usages pourtant courante a un état sous-jacent **observé** :
- Étiquetage manuel (segmentation pré-annotée par un expert).
- Données simulées à partir d'un modèle connu (états ground-truth).
- Datasets pré-segmentés (e.g. transcriptions phonétiques alignées en
  reconnaissance vocale).

Dans ce cas, le MLE est **closed-form** : pas besoin d'EM, juste compter
les transitions et estimer les paramètres d'émission par état observé.
Une seule passe, déterministe, beaucoup plus rapide.

## Décision

Étendre l'API publique :

```python
hmm_core.fit.fit(topology, X, *, states=None, ...) -> FittedModel
```

- `states=None` (défaut) → unsupervised, Baum-Welch via le backend (comportement v0.1).
- `states=array de shape (T,) avec valeurs dans [0, K)` → **supervised**,
  closed-form MLE en une passe. Déterministe; pas de `progress_callback`.

Une seconde méthode `fit_supervised(...)` est ajoutée au protocole
`HMMBackend` (cf. ADR-0003). L'implémentation `HmmlearnBackend.fit_supervised`
fait le calcul en numpy pur (pas d'EM, pas d'hmmlearn pour cette branche),
puis construit un `Constrained*HMM` avec les paramètres pré-posés et
`init_params=""` pour qu'aucun consommateur ne réinitialise par accident.

### Estimateurs (par émission)

| Émission | Transitions | Émissions |
|---|---|---|
| Gaussian | counts `(states[t], states[t+1])` normalisés par état, mask appliqué | per-state means + covariances empiriques (helper `_empirical_covars` réutilisé de l'init) |
| Multinomial | idem transitions | per-state empirical `emissionprob_` avec Laplace `+1e-6` smoothing |
| Poisson | idem transitions | per-state mean count, clip à `1e-6` |
| GMM | non implémenté | NotImplementedError → prévu Phase **A.7.1** |

### Garanties

- **Respect du mask** : si `states` contient une transition sur un edge
  interdit par `topology.allowed_transitions`, `fit_supervised` lève
  `ValueError` en listant jusqu'à 5 transitions fautives.
- **Lengths** : supporté de la même manière qu'unsupervised — les
  transitions traversant les frontières de séquences ne sont pas comptées.
- **Idempotence** : appel `fit(topo, X, states=labels)` deux fois donne
  un résultat byte-identical (déterministe par construction).

### Semi-supervised (Phase A.7.1, futur)

Si `states` contient des NaN (positions non-labellées), comportement à
définir : EM contraint sur les positions NaN + counts fixes sur les
positions labellées. **Pas implémenté**; lève `NotImplementedError` avec
message clair.

## Alternatives considérées

- **Ne pas implémenter du tout** (rester unsupervised-only). Rejeté : c'est
  une régression vs l'état de l'art (hmmlearn supporte historiquement le
  scoring d'un modèle "supervisé" via parameter pre-setting + `init_params=""`,
  mais c'est manuel et indocumenté).
- **API séparée `fit_supervised(...)`** au lieu d'un paramètre `states`.
  Rejeté : le caller a en pratique le même problème (mêmes hyperparams,
  même topology), donc une seule entrée publique est plus ergonomique.
- **Auto-détection unsupervised vs supervised** par la présence ou non
  de NaN dans X. Rejeté : ambigu (NaN peut signifier missing data).
- **Bayesian / MAP estimation** (Dirichlet prior sur transmat). Reporté
  → phase ultérieure si demandé.

## Conséquences

### Positives

- Cas d'usage important débloqué (étiquetage manuel, données simulées).
- Très rapide vs EM : une passe, pas de boucle de convergence.
- Détermine — pas de seed-dépendance.
- Tests faciles à écrire : on sait exactement ce qu'on devrait obtenir
  (counts ÷ totals).

### Négatives

- Surface d'API plus grande sur la fonction publique `fit` (un paramètre
  de plus, branchement interne). Mitigé par un docstring précis.
- GMM laissé à l'écart (`NotImplementedError`) : message clair mais
  surprenant pour qui utilise GMM. À couvrir en Phase A.7.1.
- Pas de gestion des partial labels (NaN) → seul "tout-or-rien" pour
  l'instant. Documenté.

## Tests qui valident cette décision

- `tests/test_supervised.py` (Phase A.7) :
  - Gaussian/Multinomial/Poisson — paramètres recouvrent bien les
    statistiques empiriques.
  - Mask respect — observation d'une transition interdite → `ValueError`.
  - Multi-séquences avec `lengths` — boundaries respectées.
  - GMM → `NotImplementedError` (test explicite).

## Revisit triggers

- Demande de support semi-supervised (NaN partiels) → ouvrir Phase A.7.1
  pour spécifier le modèle (probable : EM constraint + log-likelihood
  contribution différente pour les positions labellées).
- Demande d'estimateur MAP avec prior (Dirichlet sur A, Normal-Wishart sur
  émissions) → ouvrir Phase A.7.2 ou un nouveau projet "hmm-bayes".

## Pointeurs

- `src/hmm_core/fit/__init__.py` (entrée publique `fit(states=...)`)
- `src/hmm_core/backends/hmmlearn_backend.py:fit_supervised`
- `tests/test_supervised.py`
- ADR-0003 (le protocole `HMMBackend` qui rend tout ça propre) :
  [0003-backend-abstraction.md](0003-backend-abstraction.md)
