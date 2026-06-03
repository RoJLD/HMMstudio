---
Status: current
---

# Add `dcor` (distance correlation) as an alternative criterion in `unsupervised_feature_selection`

*Spec écrite le 2026-05-28. Sous-projet **C** de la réutilisation du travail de
Nathan dans hmm_studio (voir le découpage A/B/C/D dans le projet voisin
`Experiment.Crypto.2026S1.NathanBerbinau`). A (re-benchmark) et B (leçons Academy 14/15)
sont livrés. D (backend rSLDS) reste indépendant.*

## 1. Contexte / problème

`hmm_core.features.unsupervised_feature_selection()` regroupe les features candidates
par information mutuelle normalisée (NMI) via l'estimateur k-NN de Kraskov et al.
2004 (qui sous-tend `sklearn.feature_selection.mutual_info_regression`), puis garde un
médoïde par cluster. La fonction est livrée et testée, et la leçon Academy 13 la
documente.

Limites pratiques de l'estimateur NMI sur des données réelles :
- Sensible aux **doublons exacts** → nécessite un jitter gaussien sur les features
  standardisées (le module en injecte 1e-8 par défaut).
- Sensible au choix de **k** (nombre de voisins) → biais/variance qui dépend du
  régime de l'échantillon.
- Estimation **stochastique** : les résultats varient avec le seed du jitter et de
  l'estimateur k-NN.

Le travail de Nathan (`Projet_Robin/UnsupervisedModelFinder.ipynb`) est passé
empiriquement de MI/linfoot à `dcor.distance_correlation` (Székely-Rizzo-Bakirov 2007)
parce que ces instabilités lui causaient des regroupements non reproductibles. La
distance correlation a deux propriétés qui résolvent ces points :
- **Déterministe** : pas d'estimation par k-NN, pas de jitter ; `dcor(x, y)` est une
  fonctionnelle des distances pair-à-pair.
- **Caractérise l'indépendance** : `dcor(x, y) = 0` ⇔ X et Y indépendantes (au sens
  fort, pas seulement décorrélées linéairement comme Pearson).

Le coût : `O(n²)` par paire de features (calcul de matrices de distances), donc plus
lent que k-NN MI quand `n` est grand (typiquement n ≳ quelques 10⁴ devient lourd).

Aujourd'hui, l'utilisateur de `hmm_core.features` n'a qu'une seule option (NMI).
L'objectif de C est de lui offrir le choix, sans déprécier NMI.

## 2. Objectif

Ajouter un paramètre `criterion: str = "nmi"` à `unsupervised_feature_selection()`
acceptant `"nmi"` (défaut, comportement actuel inchangé) ou `"dcor"`. Cantonner la
dépendance `dcor` à un extra optionnel `[dcor]`. Mettre à jour la leçon Academy 13 et
la bibliographie pour enseigner le choix entre les deux critères avec le trade-off.

Succès = un utilisateur peut faire :
```python
unsupervised_feature_selection(df, n_clusters=8, criterion="dcor")
```
après `pip install "hmm-studio[dcor]"`, et obtenir le même type de résultat avec une
matrice de similarité dcor à la place de NMI ; la leçon 13 explique honnêtement quand
préférer l'un ou l'autre.

## 3. Design

### 3.1 API et signature

```python
unsupervised_feature_selection(
    features: pd.DataFrame,
    n_clusters: int = 10,
    *,
    criterion: str = "nmi",       # NOUVEAU
    n_neighbors: int = 5,         # ignoré si criterion == "dcor"
    linkage_method: str = "average",
    jitter_std: float = 1e-8,     # ignoré si criterion == "dcor"
    random_state: int = 42,       # ignoré si criterion == "dcor"
) -> FeatureSelectionResult
```

- `criterion ∉ {"nmi", "dcor"}` → `ValueError`.
- `criterion == "dcor"` rend `n_neighbors`, `jitter_std` et `random_state` inertes
  (dcor est déterministe et n'a pas besoin de jitter). Documenté en docstring ; pas de
  warning à l'usage (YAGNI).
- Signature *backward-compatible* : tout appel existant continue à fonctionner à
  l'identique (defaut `"nmi"`).

### 3.2 Refactor interne (sépare le « comment on mesure » du « comment on cluster »)

Extraire le pipeline `similarité → distance → linkage → fcluster → médoïdes` dans un
helper privé :

```python
def _cluster_and_pick_medoids(
    similarity_matrix: np.ndarray,   # (p, p) symétrique, [0, 1], 1 sur la diagonale
    columns: list[str],
    n_clusters: int,
    linkage_method: str,
) -> tuple[dict[int, str], dict[int, list[str]], list[str]]:
    """Renvoie (medoid_per_cluster, cluster_dict, selected_names)."""
```

Les deux branches NMI / dcor construisent leur matrice de similarité (`_nmi_matrix`,
`_dcor_matrix`) puis appellent ce helper unique. Le code de clustering+médoïde n'est
écrit qu'une fois.

### 3.3 Builder dcor

```python
def _dcor_matrix(standardized: np.ndarray) -> np.ndarray:
    """Matrice (p, p) de dcor pair-à-pair. Symétrique, [0, 1], 1 sur la diagonale."""
    import dcor  # lazy
    p = standardized.shape[1]
    M = np.zeros((p, p))
    for i in range(p):
        M[i, i] = 1.0
        for j in range(i + 1, p):
            d = dcor.distance_correlation(standardized[:, i], standardized[:, j])
            M[i, j] = d
            M[j, i] = d
    return M
```

- `import dcor` paresseux, dans la fonction. Si manquant → `ImportError` rattrapée et
  re-levée avec un message actionnable :
  `"criterion='dcor' requires the 'dcor' extra: pip install 'hmm-studio[dcor]'"`.
- Pas de standardisation interne : on réutilise le `standardized` du chemin commun
  (StandardScaler + jitter — le jitter ne gêne pas dcor et garde le code droit).
  Alternative envisagée : passer les valeurs brutes pour dcor. Rejeté pour ne pas
  diverger des inputs et pour la simplicité.

### 3.4 `FeatureSelectionResult` : renommer le champ + alias backward-compat

```python
@dataclass(frozen=True)
class FeatureSelectionResult:
    selected: pd.DataFrame
    similarity_matrix: np.ndarray              # NOUVEAU nom canonique
    cluster_dict: dict[int, list[str]]
    medoid_per_cluster: dict[int, str]

    @property
    def nmi_matrix(self) -> np.ndarray:
        """Alias legacy de `similarity_matrix`. Conservé pour compat."""
        return self.similarity_matrix
```

- Field renommé `nmi_matrix → similarity_matrix` (le nom NMI était impropre dès qu'un
  autre critère existe).
- Property `nmi_matrix` conservée pour que tout code consommateur existant
  (`result.nmi_matrix`) continue à fonctionner sans modification.
- Pas de `DeprecationWarning` (YAGNI ; l'alias est silencieux, juste documenté).

### 3.5 Prep op (`src/hmm_core/prep/ops.py`)

L'op YAML `select_features_unsupervised` gagne un champ `criterion` :
```yaml
steps:
  - op: dropna
  - op: select_features_unsupervised
    n_clusters: 8
    criterion: dcor      # NOUVEAU (défaut : "nmi")
```

Passé-thru à `unsupervised_feature_selection`.

### 3.6 Dépendance optionnelle (`pyproject.toml`)

Ajouter dans `[project.optional-dependencies]` :
```toml
dcor = ["dcor>=0.6"]
```

Suit le pattern existant (`bayesian = [...]`). Aucune dépendance runtime ajoutée à la
base install ; l'utilisateur qui veut dcor fait `pip install "hmm-studio[dcor]"`.

### 3.7 Tests (`tests/test_features.py`)

- **Paramétrer** les tests d'invariants génériques sur `criterion ∈ {"nmi", "dcor"}`
  via `@pytest.mark.parametrize` : (a) selected ⊂ input columns, (b) `n_clusters`
  colonnes retenues, (c) features parfaitement corrélées → 1 médoïde par groupe.
- **Tests dcor-spécifiques** : `similarity_matrix` symétrique, valeurs dans [0, 1],
  `dcor(x, x) = 1` sur la diagonale.
- **Test backward-compat** : `result.nmi_matrix` retourne `result.similarity_matrix`
  (alias).
- **Test gating** : les tests dcor utilisent `pytest.importorskip("dcor")` pour être
  skipped (pas failed) si l'extra n'est pas installé.
- **Test prep op** : la pipeline YAML avec `criterion: dcor` produit le bon résultat.

### 3.8 Leçon 13 (`lesson-13-choosing-features.tsx`)

Ajouter une nouvelle section après « When to use it — and when not to », avant
« Where to learn more » :

> **Alternative criterion : distance correlation**
>
> NMI is not the only way to measure shared information. The selector also accepts
> `criterion="dcor"`, which uses **distance correlation** (Székely-Rizzo-Bakirov 2007)
> instead. dcor is :
> - **Deterministic** : a closed-form functional of pairwise distances. No k-NN
>   estimator, no jitter, no `random_state` to worry about.
> - **Characterises independence** : `dcor(X, Y) = 0` iff X and Y are independent
>   (not just linearly uncorrelated).
>
> The trade-off : dcor is `O(n²)` per pair (vs k-NN MI's `~O(n log n)`), so on very
> large samples NMI is faster.
>
> Usage :
> ```python
> # Install the optional extra first :
> #   pip install "hmm-studio[dcor]"
> result = unsupervised_feature_selection(df, n_clusters=8, criterion="dcor")
> ```
>
> When to prefer dcor : small-to-medium samples where reproducibility matters and
> the NMI k-NN estimator's jitter sensitivity bites. When to prefer NMI : very large
> samples where the `O(n²)` per pair becomes the bottleneck.

Mettre à jour le bloc existant « Using it in a prep recipe » pour signaler que
`criterion: dcor` y marche aussi.

### 3.9 Bibliographie (`docs/sources/academy-references.md`)

- Nouvelle entrée Tier-3 :
  ```
  ### Székely, Rizzo & Bakirov 2007 — *Measuring and testing dependence by correlation of distances*

  Gábor J. Székely, Maria L. Rizzo, Nail K. Bakirov. *Annals of Statistics* 35(6),
  2769–2794.

  Introduces distance correlation, a measure that characterises independence (zero
  iff X⊥Y, not just uncorrelated) and works on continuous and categorical data
  without density estimation. The Python `dcor` package (Carreño et al.) implements
  it for practical use. Underlies the `criterion="dcor"` option of
  `unsupervised_feature_selection`.

  — **PDF** : <https://projecteuclid.org/journals/annals-of-statistics/volume-35/issue-6/Measuring-and-testing-dependence-by-correlation-of-distances/10.1214/009053607000000505.full>
  ```
- Mettre à jour la ligne 13 de la table per-leçon : ajouter `Székely-Rizzo-Bakirov 2007`.

### 3.10 Update de la spec existante (`docs/specs/2026-05-27-unsupervised-feature-selection.md`)

Append en bas une section `## Update 2026-05-28 — dcor as alternative criterion` qui
résume : motivation (instabilités MI/jitter observées par Nathan), API choisie
(`criterion` param + extra optionnel), renommage `nmi_matrix → similarity_matrix` avec
alias backward-compat.

### 3.11 Alternatives considérées

- **Fonction séparée `unsupervised_feature_selection_dcor()`** : duplication de code,
  pas de surface API unifiée. Rejeté.
- **Param `criterion` SANS refactor** : `if criterion == "dcor"` direct dans la
  fonction. Marche, mais le code de clustering+médoïde finit dupliqué entre branches.
  Rejeté au profit de l'extraction `_cluster_and_pick_medoids`.
- **Dependance runtime obligatoire** : ajouter `dcor>=0.6` à `dependencies`. Rejeté
  pour garder la base install minimale (pattern `[bayesian]` extra déjà établi).
- **Ne PAS renommer `nmi_matrix`** : garder le nom et documenter qu'il contient le
  critère choisi. Rejeté — nom impropre dès qu'on n'a pas du NMI. La property alias
  conserve la backward-compat sans le coût du nom impropre.

## 4. Scope boundaries

- **Out** : benchmark empirique « NMI vs dcor sur jeu de données réel » (follow-up
  possible, mais ce n'est pas un changement de code).
- **Out** : composant React interactif dans la leçon 13 (pure text update).
- **Out** : autres critères de similarité (linfoot, distance covariance non
  corrélée, HSIC, …). On ajoute dcor parce que Nathan l'a validé empiriquement ; pas
  de zoo de critères sans cas d'usage.
- **Out** : `select_features_unsupervised_dcor` op séparée ; on passe par `criterion`.
- **Out** : modification de la signature ou du type de retour pour d'autres champs.

## 5. Open questions (défauts retenus — à confirmer à la relecture)

1. **Standardisation pour dcor** : *défaut retenu* — on réutilise le `standardized`
   (StandardScaler + jitter) du chemin commun. Alternative : passer les valeurs brutes
   pour dcor (dcor est invariant par changement d'échelle isotrope, donc neutre).
   Le défaut garde le code droit ; à confirmer.
2. **Borne sur la dimension** : *défaut retenu* — pas de garde explicite, dcor est
   O(n² · p²). Sur `p ≳ 100` × `n ≳ 50000` ça devient sensible. On documente la
   limite dans la docstring sans la garder en code.
3. **PDF URL Székely** : *défaut retenu* — le lien projecteuclid (canonique, page de
   l'article). À remplacer par un mirror si le projecteuclid est instable.
