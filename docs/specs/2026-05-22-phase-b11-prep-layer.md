# Phase B.11 — Data preparation layer (recipes engine + library)

**Date** : 2026-05-22
**Auteur** : Robin Denis (avec architecte-CEO framing)
**Status** : ✅ **SHIPPED 2026-05-22 — engine + 8 bundled recipes + 21 ops**
**Effort réel** : ~1 jour
**Prérequis durs** : aucun

---

## 1. Positionnement

`hmm-studio` ajoute une couche de préparation de données **general-purpose,
composable, recipe-driven** entre le warehouse (B.10) et le moteur HMM.
L'architecture est **100 % générale** (pas HMM-spécifique), mais la library
des recipes shippées privilégie les workflows HMM-canoniques pour servir
le wedge.

### Le piège évité

"Outil de data preparation" est une catégorie immense (pandas, dbt, Beam,
Prefect, sklearn-preprocessing, tsfresh). Si on y va sans frein, on dilue
le wedge HMM en construisant un mini-pandas qui ne sera jamais aussi bon
que pandas.

**Le bon framing** : un **thin layer au-dessus de pandas**, avec recipes
déclaratives composables. L'utilisateur reste maître — il peut toujours
descendre en pandas pur via le Python escape hatch.

## 2. Architecture livrée

```
hmm_core.prep
├── ops.py           # 21 ops atomiques (pandas-thin functions)
├── engine.py        # YAML parser + Pipeline executor + composition recursive
├── recipes/         # 8 recipes YAML bundled
│   ├── normalize_zscore.yaml
│   ├── clean_missing_forward_fill.yaml
│   ├── outlier_robust_winsorize.yaml
│   ├── financial_log_returns.yaml
│   ├── volatility_features.yaml
│   ├── crypto_basic_prep.yaml          ← composé via includes
│   ├── align_to_grid_daily.yaml
│   └── financial_full_features.yaml    ← composé multi-window
└── __init__.py      # Public API : Pipeline, Recipe, list_recipes, load_recipe
```

### 21 ops atomiques

| Catégorie | Ops |
|---|---|
| Column manipulation | `select_columns`, `drop_columns`, `rename_columns` |
| Missing data | `fillna_forward`, `fillna_backward`, `fillna_value`, `interpolate`, `dropna` |
| Transformations | `log_diff`, `diff`, `pct_change`, `log_transform`, `shift` |
| Rolling features | `rolling_mean`, `rolling_std`, `ewma` |
| Scaling | `zscore`, `minmax`, `robust_scale` |
| Outlier handling | `winsorize`, `clip` |
| Time / resampling | `resample` |

Chaque op = `(df: pd.DataFrame, **params) -> pd.DataFrame`. Enregistrement
via `@register_op("name")`. L'utilisateur peut ajouter ses propres ops via
le même décorateur.

### 8 recipes bundled

**Generaux** (4) :
- `normalize_zscore` — z-score sur colonnes spécifiées
- `clean_missing_forward_fill` — forward-fill puis dropna
- `outlier_robust_winsorize` — winsorize 1%/99% puis z-score
- `align_to_grid_daily` — resample daily mean

**HMM-canoniques / finance** (4) :
- `financial_log_returns` — log-diff(close) + dropna
- `volatility_features` — rolling_std sur log_return (window=20)
- `crypto_basic_prep` — **composé** : log_returns + vol + zscore + dropna
- `financial_full_features` — **composé** : log_returns + multi-window vol + winsorize + zscore

### Composition via `includes`

```yaml
name: crypto_basic_prep
includes:
  - recipe: financial_log_returns
  - recipe: volatility_features
steps:
  - op: zscore
    columns: [log_return, realized_vol_20]
  - op: dropna
output:
  observations: [log_return]
  covariates: [realized_vol_20]
```

Résolution récursive avec garde-fou anti-cycle (depth max 8). Les recipes
inclus sont expansés inline avant les steps locaux.

### Output split (observations / covariates)

Le champ `output:` permet de produire directement les arrays X et Z
consommables par `fit(topo, X)` et `fit_nhmm(topo, X, Z)`. Le `PreparedResult`
expose `.df`, `.X`, `.Z`, `.provenance`.

### Provenance / sidecar

`PreparedResult.to_sidecar(output_path)` écrit un YAML `<path>.recipe.yaml`
documentant la séquence exacte de steps appliqués avec leurs paramètres
résolus. Reproductibilité complète.

## 3. Usage

### Library (YAML by name)

```python
from hmm_core.prep import Pipeline
pipe = Pipeline.from_recipe("crypto_basic_prep")
result = pipe.fit_transform(raw_df)
X, Z = result.X, result.Z
```

### File path

```python
pipe = Pipeline.from_yaml("path/to/my_recipe.yaml")
result = pipe.fit_transform(raw_df)
```

### Python escape hatch

```python
pipe = (
    Pipeline()
    .add_step("log_diff", column="close", new_name="ret")
    .add_step("rolling_std", column="ret", window=20)
    .add_step("zscore", columns=["ret", "rolling_std_ret_20"])
    .add_step("dropna")
    .set_output(observations=["ret"], covariates=["rolling_std_ret_20"])
)
result = pipe.fit_transform(raw_df)
```

### Discovery

```python
from hmm_core.prep import list_recipes
print(list_recipes())  # 8 bundled recipes listed
```

### Custom op registration

```python
from hmm_core.prep import register_op

@register_op("my_custom_transform")
def my_op(df, *, factor: float = 1.0):
    return df * factor

# Now usable in YAML or Python pipelines
```

## 4. Tests livrés

`tests/test_prep.py` — **42 tests**, tous verts :
- Ops atomiques : 20 tests (un par op + edge cases)
- Pipeline Python API : 4 tests
- Recipe library discovery + run : 4 tests
- Composition : 3 tests
- YAML loading edge cases : 6 tests (unknown name/op, invalid root, cycle)
- Provenance + sidecar : 2 tests
- register_op extensibility : 2 tests
- Integration end-to-end avec `fit()` : 1 test

## 5. Anti-scope-creep guardrails (à respecter)

| ❌ Hors-scope | Pourquoi |
|---|---|
| DSL custom de feature engineering | Pandas/sklearn existent déjà |
| Scheduling / batch / cron | Use Airflow/Prefect ; out of scope |
| Multi-dataset joins | Pandas/dbt territory |
| ML model fitting dans les recipes | Recipes = transforms only |
| Time-aware CV splits | C'est modeling, pas prep |
| GUI drag-drop DAG editor | YAML suffit ; ré-évaluer en B.11.b |
| Versioning git-like des recipes | Le sidecar yaml + git external |
| Streaming / incremental compute | Tout est in-memory pandas pour MVP |

## 6. B.11.b (UI) — différé

L'UI integration (tab "Prep" dans le studio web, recipe browser, live
preview, sidecar éditable) est volontairement déférée. Le moteur engine-only
(B.11.a) est utilisable :
- Via la Python API (Robin, chercheurs, devs)
- Via la CLI éventuellement (à brancher dans `hmm-fit run --recipe ...`)
- Plus tard intégrée dans le studio web (B.11.b)

## 7. Successeurs hors-scope (à gater sur usage)

- **B.11.b** : UI integration dans le studio web (1 semaine, à démarrer post-B.10)
- **B.11.1** : CLI flag `hmm-fit prep recipe data.csv --output prepared.parquet`
  (0.5 jour, à ajouter quand demande réelle)
- **B.11.2** : Plus de recipes shippés (bio, NLP, sensor) — gated sur signal
  utilisateur externe
- **B.11.3** : Validation de schéma sur les recipes (e.g. JSON schema) —
  utile si recipes deviennent partagés
- **B.11.4** : Versioning des recipes avec migrations — gated sur breaking
  changes du schéma

## 8. ADR à créer

`docs/decisions/0011-prep-layer-scope.md` :
- Pourquoi engine general + library HMM-focused (vs HMM-only narrow) ?
- Pourquoi YAML-first + Python escape hatch (vs Python-only ou YAML-only) ?
- Pourquoi pas pandas-fork ou sklearn-Pipeline-subclass ?
- Comment ajouter une nouvelle op / recipe sans casser le contract ?

## 9. Intégration future avec B.10 (warehouse)

Quand B.10 ship la UI warehouse :
- Recipes vivent à côté des datasets dans le warehouse (`recipes/` subfolder)
- Bouton "Apply recipe" dans le tab Data — sélectionner dataset + recipe → output dataset stocké
- Sidecar `.recipe.yaml` exposé dans le sidecar metadata viewer
- Bouton "Use in fit" pré-rempli avec le X/Z du output

Pour l'instant : recipes sont bundled in-package, l'utilisateur charge ses
propres recipes depuis un path.
