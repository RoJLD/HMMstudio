# ADR-0014 : Student-t / Skew-T emissions — code gated

**Status** : SPEC-ONLY · code **GATED**
**Date** : 2026-05-27
**Related** : [ADR-0005 per-state EmissionSpec](0005-per-state-emissions-scope.md), [ADR-0007 GMM-NHMM](0007-gmm-nhmm-scope.md), [ADR-0001 hmmlearn patch](0001-backend-hmmlearn-patch.md)

## Contexte

hmm-studio expose quatre types d'émission : Gaussian, GMM, Multinomial,
Poisson. Tous reposent sur des subclasses `Constrained*HMM` d'hmmlearn
(ADR-0001).

Pour les données financières — le use case crypto de Robin, la recherche
Nathan/Valentin — l'hypothèse gaussienne est **empiriquement fausse sur
les queues**. Les log-returns crypto ont :
- des **queues lourdes** (kurtosis ≫ 3 : krachs et pumps bien plus
  fréquents qu'une gaussienne ne le prédit),
- souvent une **asymétrie** (skew : les krachs sont plus violents que les
  rallyes).

Fitter une émission gaussienne sur ça sous-estime le risque de queue :
le modèle "lisse" les événements extrêmes dans une variance trop large.

La recherche Nathan a construit une `DiagonalSkewTObservations` (queues
lourdes + asymétrie + valeurs négatives) — mais contre la lib `ssm`
(Linderman), pas hmmlearn. Voir
`Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/ssm_extensions.py`.

### Pourquoi cette ADR existe (et pourquoi c'est gated)

Une émission Student-t est **dans le wedge** (c'est juste un type
d'émission HMM de plus, pas un pivot vers SSM/Transformer — distinction
clé vs le rSLDS rejeté). Donc pas de question de scope-discipline ici.

La question est l'**effort vs le besoin** :
- hmmlearn **n'a pas** de Student-t natif. On l'implémenterait
  from-scratch en subclassant `BaseHMM`.
- Le M-step Student-t est un **EM-dans-l'EM** : la loi de Student est un
  mélange d'échelle de gaussiennes, donc le M-step nécessite des poids
  de précision auxiliaires `u_t = (ν+1)/(ν + δ_t²)` (E-step interne) puis
  un solve 1-D pour le degré de liberté `ν`. Non-trivial : ~250-400 LOC +
  validation numérique soignée.
- **GMM approxime déjà les queues lourdes** : un mélange à 2-3 composantes
  par état capture une bonne partie de l'excès de kurtosis (c'est le
  workaround actuel, livré en A.10).

Donc on spec maintenant (pensée tracée, contour clair), on code quand un
trigger fire.

## Décision

### Scope si on l'implémente

Deux saveurs, par ordre de priorité :

1. **`studentt`** — Student-t symétrique, diagonale. Queues lourdes,
   pas d'asymétrie. Le cas le plus courant et le plus simple.
2. **`skewt`** — Skew-T diagonale (la version Nathan). Queues lourdes +
   asymétrie. Plus complexe (paramètre de skew `α` par état/feature).
   **Déféré** à une sous-décision même si `studentt` est construit.

### Architecture si on l'implémente

`hmm_core.fit.studentt.ConstrainedStudentTHMM`, subclass de
`hmmlearn.base.BaseHMM` (PAS de `GaussianHMM` — l'émission diffère) :

```
ConstrainedStudentTHMM(BaseHMM)
    paramètres par état : mu (K, D), sigma (K, D), nu (K, D)  [diagonale]
    _compute_log_likelihood : scipy.stats.t.logpdf vectorisé
    _do_mstep :
        E-step interne : u_t = (nu+1) / (nu + ((x-mu)/sigma)^2)
        M-step : mu, sigma pondérés par u_t ; nu par solve 1-D
                 (digamma equation) ; PUIS _apply_mask sur transmat
                 (cohérent avec les autres Constrained*HMM)
```

- Respect du masque : identique aux autres subclasses (mask appliqué dans
  `_do_mstep` après l'update transmat).
- Lengths multi-séquences : hérité du `BaseHMM`.
- Topology : `EmissionSpec(type="studentt", n_features=D)` ; pas de
  `covariance_type` (diagonale seulement en v1 ; full-covariance Student-t
  = encore plus lourd, déféré).

### Validation si on l'implémente

`validation/test_v8_studentt.py` :
- recovery sur données simulées Student-t (ν connu, recouvrer ν à ±20%)
- cross-check : sur données gaussiennes (ν → ∞), `studentt` doit
  converger vers les mêmes paramètres que `gaussian` à tolérance large
- tail test : sur returns crypto réels, le QQ-plot des résidus standardisés
  doit être plus droit que pour `gaussian`

## Gating criteria

Le code commence dès qu'**au moins un** :

1. **Signal externe** — issue/email demandant explicitement des émissions
   heavy-tailed / Student-t.
2. **Évidence interne de sous-fit GMM** — sur les données de Robin, un
   GMM à `n_mix ≥ 2` rate matériellement les queues (QQ-plot des résidus
   nettement courbé aux extrémités, ou un backtest de risque qui
   sous-estime les drawdowns). C'est le trigger le plus probable.
3. **Cas de validation** — un dataset canonique (financier ou bio) où la
   Student-t bat la gaussienne/GMM sur un critère objectif (log-lik
   out-of-sample, calibration de VaR).

Si aucun trigger à M+6 mois (2026-11-27) : revisiter (maintenir / DEFER /
fermer).

## Alternatives rejetées / différées

| Alternative | Verdict |
|---|---|
| **GMM 2-3 composantes comme approximation** | C'est le **workaround actuel** (livré A.10). Suffisant pour beaucoup de cas. La Student-t native est un raffinement, pas un remplacement. |
| **Wrapper la lib `ssm` (version Nathan)** | Ajoute `ssm` comme dépendance, EM différent (variationnel), pas d'intégration mask native. Rejeté pour la même raison que le fork dynamax dans [ADR-0013](0013-jax-backend-scope.md) : on garde le contrôle dans notre framework `Constrained*HMM`. |
| **dynamax (via futur JaxBackend ADR-0013)** | dynamax n'a pas de Student-t natif non plus. Si JaxBackend existe un jour, Student-t-en-JAX serait une sous-décision distincte. |
| **Skew-T directement en v1** | Trop lourd d'un coup. `studentt` symétrique d'abord ; `skewt` déféré. |
| **Full-covariance Student-t** | Multivariée à queues lourdes = matrice d'échelle + ν partagé, M-step nettement plus dur. Diagonale seulement en v1. |

## Conséquences

### Positives (si construit)
- Émission honnête pour la finance (queues lourdes = le risque de queue
  est *le* sujet en crypto/trading).
- 5ème type d'émission → couverture plus complète que hmmlearn vanilla.
- Renforce le wedge "deepest HMM library".

### Négatives / coût accepté
- M-step Student-t non-trivial (EM-dans-EM) → surface de bug numérique
  (le solve sur ν peut diverger ; il faut clamper).
- Maintenance d'une subclass `BaseHMM` from-scratch (vs hériter de
  `GaussianHMM`).
- GMM couvre déjà partiellement le besoin → ROI à confirmer par un trigger.

### Réversibilité
Émission additive : si jamais insoutenable, on retire le type `studentt`
de `_CLASS_BY_EMISSION`, on garde l'ADR. Aucun modèle gaussien/GMM/etc.
n'est affecté.

## Pointeurs

- `src/hmm_core/fit/gaussian.py` — modèle de subclass `Constrained*HMM`
  à imiter (mais hériter de `BaseHMM`, pas `GaussianHMM`)
- `src/hmm_core/fit/poisson.py` — exemple d'émission non-gaussienne déjà
  faite (le pattern le plus proche)
- `Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/ssm_extensions.py`
  — `DiagonalSkewTObservations` (référence skew-t, lib ssm)
- [ADR-0007 GMM-NHMM](0007-gmm-nhmm-scope.md) — le workaround heavy-tail actuel
- Liu & Rubin (1995), "ML estimation of the t distribution using EM" — la
  référence pour le M-step (E-step de précision + solve ν)
