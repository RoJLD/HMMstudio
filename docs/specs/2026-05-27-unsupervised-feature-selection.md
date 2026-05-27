# Unsupervised feature selection for HMM inputs — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis (porté depuis la recherche crypto Nathan/Robin)
**Status** : SPEC DRAFTED · prêt à implémenter
**Effort estimé** : ~1-2 jours
**Prérequis durs** : B.11 prep layer (livré), `hmm_core.fit`

---

## 1. Contexte et problème

Le prep layer (B.11) nettoie et transforme les colonnes (`log_diff`,
`zscore`, `rolling_mean`, …) mais ne répond pas à la question qui vient
juste avant le fit : **quelles features donner au HMM ?**

Aujourd'hui l'utilisateur choisit ses colonnes à la main. Avec un dataset
on-chain crypto à 30-40 indicateurs (cf. `Eth output indicators.csv` de
Valentin : 29 colonnes), c'est :
- de la friction (essai-erreur manuel),
- une source de fuite de variance (features fortement corrélées →
  redondance qui gonfle la dimension d'émission sans ajouter
  d'information),
- non reproductible (le choix n'est documenté nulle part).

La recherche crypto (repos Nathan `Projet_Robin/` + Robin
`cmex_crypto/features/unsupervised_selection.py`) a construit un
**sélecteur de features non-supervisé** : clustering des features par
information mutuelle, puis un représentant (médoïde) par cluster. C'est
exactement le chaînon manquant côté hmm-studio.

## 2. Goal

Porter ce sélecteur dans `hmm_core` comme une capacité first-class,
réutilisable et testée, qui prend un DataFrame de features candidates et
retourne un sous-ensemble décorrélé — prêt à alimenter `fit()`. Zéro
nouvelle dépendance (sklearn déjà présent). Discoverable via le top-level
package et utilisable depuis une recette prep.

## 3. Design

### 3.1 Module principal : `hmm_core/features.py`

Fonction publique :

```python
def unsupervised_feature_selection(
    features: pd.DataFrame,
    n_clusters: int = 10,
    n_neighbors: int = 5,
    linkage_method: str = "average",
    jitter_std: float = 1e-8,
    random_state: int = 42,
) -> FeatureSelectionResult: ...
```

Algorithme (repris de `unsupervised_selection.py`, version NMI/sklearn —
PAS la version dcor de Nathan, voir § 4) :

1. **Standardise** (`StandardScaler`) + jitter gaussien `1e-8` (le
   k-NN MI estimator de sklearn ne supporte pas les ties exacts).
2. **Entropie par variable** `H(x_i)` via MI diagonale `MI(x_i, x_i+jitter)`
   avec le même estimateur k-NN — sert de normaliseur.
3. **NMI par paire** `NMI(x_i, x_j) = MI(x_i, x_j) / sqrt(H_i · H_j)`,
   clippé dans `[0, 1]`.
4. **Distance** `D = 1 - NMI`, symétrisée, diagonale à zéro.
5. **Clustering hiérarchique agglomératif** (`scipy.cluster.hierarchy`,
   `linkage_method` défaut `"average"` — `"ward"` invalide sur distance
   NMI). Coupe à `n_clusters`.
6. **Médoïde par cluster** = la feature avec la plus forte NMI moyenne
   au reste de son cluster (centralité).

### 3.2 Résultat : dataclass `FeatureSelectionResult`

```python
@dataclass(frozen=True)
class FeatureSelectionResult:
    selected: pd.DataFrame          # features[médoïdes], index préservé
    nmi_matrix: np.ndarray          # (p, p), NMI(x_i, x_i) = 1
    cluster_dict: dict[int, list[str]]      # cluster_id -> noms de features
    medoid_per_cluster: dict[int, str]      # cluster_id -> médoïde
```

Le résultat riche (matrice NMI + clusters) permet un heatmap diagnostique
et l'inspection de "pourquoi telle feature a été retenue".

### 3.3 Intégration prep (thin wrapper)

Pour l'usage en recette YAML, ajouter un op prep
`select_features_unsupervised` qui wrappe la fonction et ne retourne que
le sous-ensemble de colonnes (signature prep `df -> df`) :

```yaml
steps:
  - op: select_features_unsupervised
    n_clusters: 8
```

L'op délègue à `unsupervised_feature_selection(...).selected`. Les
métadonnées riches (matrice NMI) ne sont pas exposées dans le pipeline
(les ops prep sont `df -> df`) — pour ça, l'utilisateur appelle la
fonction directement.

### 3.4 API surface

- `hmm_core.features.unsupervised_feature_selection` (exporté top-level)
- `hmm_core.features.FeatureSelectionResult`
- nouvel op prep `select_features_unsupervised` enregistré dans `OPS`

### 3.5 Academy (optionnel, même PR si temps)

Une leçon 13 "Choosing features for your HMM" qui explique le problème
(redondance corrélée), montre la heatmap NMI, et lie au notebook. Si pas
le temps, déféré — pas bloquant pour le module.

## 4. Scope boundaries (ce qu'on ne fait PAS)

- **Pas de sélection supervisée** (mRMR, target-aware) — c'est la branche
  `Features_Selection` du `ModelFinder` supervisé de Nathan. Hors scope
  ici (le wedge immédiat est unsupervised, cohérent avec le reste du prep
  layer). Déféré tant qu'il n'y a pas de signal.
- **Pas la variante dcor** (Nathan `UnsupervisedModelFinder.ipynb`).
  `dcor` est une dépendance externe en plus ; la version NMI de Robin
  utilise `sklearn.feature_selection.mutual_info_regression` déjà présent.
  On garde **zéro nouvelle dépendance**. (Note : si un jour la distance
  correlation s'avère nettement supérieure empiriquement, on reconsidère
  — mais pas par défaut.)
- **Pas de PCA** (réduction continue) — le prep layer reste pandas-only
  (rappel ADR du prep layer). PCA reste un step notebook explicite.
- **Pas de sélection de covariables NHMM par causalité** (Granger /
  Transfer Entropy de Robin) — c'est un sujet distinct (choisir les `Z`
  d'un NHMM, pas les `X`), à spec'er séparément si demandé.

## 5. Tests (`tests/test_features.py`)

| Test | Vérifie |
|---|---|
| `test_selection_returns_subset` | `selected.columns ⊆ features.columns` |
| `test_n_clusters_equals_n_selected` | `len(selected.columns) == n_clusters` |
| `test_correlated_features_collapse` | 2 colonnes quasi-identiques → une seule retenue |
| `test_independent_features_all_kept` | p features indépendantes, `n_clusters=p` → toutes retenues |
| `test_nmi_matrix_shape_and_diag` | `(p, p)`, diagonale = 1, symétrique |
| `test_medoid_is_most_central` | médoïde = max NMI moyenne intra-cluster |
| `test_n_clusters_exceeds_features_raises` | `n_clusters > p` → ValueError |
| `test_empty_features_raises` | DataFrame vide → ValueError |
| `test_prep_op_select_features_unsupervised` | op prep retourne le bon sous-ensemble, intégrable en pipeline |
| `test_reproducible_with_seed` | même `random_state` → même sélection |

## 6. Définition de "done"

- [ ] `hmm_core/features.py` : `unsupervised_feature_selection` +
      `FeatureSelectionResult`, exportés top-level.
- [ ] op prep `select_features_unsupervised` dans `prep/ops.py` + OPS.
- [ ] 10 tests dans `tests/test_features.py`, tous verts.
- [ ] Docstrings complets (cite Kraskov et al. 2004 pour le k-NN MI).
- [ ] CHANGELOG `[Unreleased]` mis à jour.
- [ ] (Optionnel) Leçon Academy 13 + entrée bibliographie.

## 7. Provenance

Porté de :
- `Experiment.Crypto.2026S1.RobinDenis/src/cmex_crypto/features/unsupervised_selection.py`
  (version production NMI, propre — base du portage)
- `Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/UnsupervisedModelFinder.ipynb`
  (prototype dcor — non retenu, voir § 4)
