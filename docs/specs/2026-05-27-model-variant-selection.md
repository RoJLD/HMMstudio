# Model-variant selection — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis (issu de l'assessment ModelFinder Nathan/Robin)
**Status** : SPEC DRAFTED · prêt à implémenter (3 phases)
**Effort estimé** : ~3-4 jours (Phase 1 ~1j, Phase 2 ~0.5j, Phase 3 ~2j)
**Prérequis durs** : `fit` / `fit_nhmm` / `fit_gmm_nhmm` / `fit_factorial_nhmm`
(livrés), HQIC (livré `e9bdc07`), K-scan infra parent/child (livrée)

---

## 1. Contexte et problème

Le K-scan compare des `K` pour **un seul** type d'émission. Mais le vrai
choix de modélisation est plus large : Gaussian vs GMM vs Poisson, et à
quel `K` ? L'utilisateur fait ça à la main aujourd'hui — fit plusieurs
specs, note les BIC dans un coin, compare.

La recherche crypto (Nathan `ModelFinder.ipynb`) a un `Model_Selection`
qui compare des modèles par critère d'information. La part **in-scope** de
cette idée — restreinte aux variants HMM — manque à hmm-studio.

### La subtilité statistique qui cadre tout

Tous les variants ne sont **pas comparables** par un même BIC/AIC/HQIC :
- **Comparables** (modélisent `P(X)` sur le même `X`) : Gaussian, GMM,
  Poisson, Multinomial. BIC/AIC/HQIC valides entre eux.
- **NHMM** modélise `P(X | Z)` — log-lik conditionné aux covariables, PAS
  sur la même échelle que `P(X)`. Comparer NHMM vs Gaussian par BIC brut
  est statistiquement faux.
- **Factorial** modélise l'espace produit joint — comparable à un HMM plat
  sur le même `X`, mais le comptage `n_params` diffère et l'interprétation
  du critère change.

**Décision** (validée) : on inclut TOUS les variants dans le tableau,
mais NHMM/Factorial sont **flaggés `comparable=False`** avec une note
explicite, et le « best by criterion » ne range **que parmi les
comparables**. L'utilisateur voit tout, mais on l'avertit que le ranking
cross-type des non-comparables est indicatif, pas rigoureux.

## 2. Goal

Donner une couche de model-selection qui fit plusieurs specs HMM
candidates sur le même `X`, les range par BIC/AIC/HQIC, gère
honnêtement la comparabilité, et est accessible depuis trois surfaces
(Python, CLI, web UI). Réutilise l'engine existant — aucune nouvelle
dépendance, aucun nouveau backend.

## 3. Design

### Phase 1 — Core Python (`hmm_core/selection.py`)

```python
@dataclass(frozen=True)
class CandidateResult:
    label: str                 # "gaussian K=3", "gmm K=2 n_mix=2", "nhmm K=3"
    kind: str                  # "gaussian" | "gmm" | ... | "nhmm" | "factorial"
    fitted: object             # FittedModel | NHMMFittedModel | GMMNHMMFittedModel | FactorialNHMMFittedModel
    log_likelihood: float
    bic: float
    aic: float
    hqic: float
    n_params: int
    comparable: bool           # True ssi modélise P(X) sur le même X
    note: str | None           # ex. "models P(X|Z), not directly comparable"

@dataclass(frozen=True)
class ModelComparison:
    candidates: list[CandidateResult]      # ordre d'insertion
    best_by_bic: str | None                # label du meilleur PARMI comparable=True
    best_by_aic: str | None
    best_by_hqic: str | None

    def ranked(self, criterion: str = "bic") -> list[CandidateResult]: ...
    def to_summary_dict(self) -> dict: ...
    def _repr_html_(self) -> str: ...      # tableau Jupyter, non-comparables grisés + ⚠

def compare_models(
    X: np.ndarray,
    candidates: list[Candidate],
    *,
    lengths: np.ndarray | None = None,
    seed: int = 42,
) -> ModelComparison: ...
```

**Candidate** = une spec à essayer. Un type union léger :
- `TopologyCandidate(topology: Topology)` — émission comparable, fit via `fit()`.
- `NHMMCandidate(topology, Z, covariate_names)` — fit via `fit_nhmm()`,
  `comparable=False`.
- `FactorialCandidate(chains, covariates_per_chain, emission, ...)` — fit
  via `fit_factorial_nhmm()`, `comparable=False`.

(GMM-NHMM = un `NHMMCandidate` avec topology GMM ; on route sur
`fit_gmm_nhmm` selon `topology.emission.type`.)

**Helper de génération de grille** :

```python
def auto_grid(
    base_topology: Topology,
    k_range: range,
    emission_types: list[str] = ["gaussian"],
    *,
    n_mix: int = 2,                 # pour les candidats gmm
) -> list[TopologyCandidate]:
    """Génère la grille comparable émission × K depuis un base spec."""
```

Produit uniquement des candidats **comparables** (émission × K). NHMM /
Factorial s'ajoutent manuellement (ils requièrent Z/chains).

**Robustesse** : un candidat dont le fit lève (non-convergence, données
incompatibles) est capturé → `CandidateResult` avec un champ d'erreur,
exclu du ranking, jamais fatal pour la comparaison entière.

### Phase 2 — CLI (`hmm-fit compare`)

```
hmm-fit compare <spec_dir> <data.csv> [--criterion bic|aic|hqic]
```

- `<spec_dir>` : dossier de `*.yaml` topologies candidates (émissions
  comparables). Optionnellement un `grid.yaml` décrivant une `auto_grid`.
- Imprime une **Rich table** ranked (comme `hmm-fit batch`) : comparables
  en haut triés par critère, non-comparables en dessous avec ⚠.
- Exit code 0 si ≥ 1 candidat comparable a convergé.
- NHMM/Factorial via CLI : hors v1 du CLI (ils nécessitent Z/chains, pas
  exprimables proprement en flat YAML dir) — note dans le `--help`.

### Phase 3 — Web UI (`/compare`)

**Résolution du problème « d'où viennent les Z/chains » dans l'UI** :
- La page `/compare` fait la **grille comparable auto-générée** : l'user
  choisit un base topology (ou en charge un), un range de K (k_min, k_max),
  et coche les types d'émission (Gaussian / GMM / Poisson). Le backend
  génère la grille via `auto_grid`.
- NHMM/Factorial **ne sont pas** dans le web UI v1. Une note sur la page :
  « pour comparer contre NHMM / Factorial (qui nécessitent des covariables
  / chaînes explicites), utilise l'API Python ou `hmm-fit compare` ».
- **Backend** : `POST /api/compare/start` (parent/children, réutilise
  l'infra K-scan), `GET /api/compare/{id}` → un `CompareResult` (children
  + best-by-criterion). Réutilise `JobRunner` parent/child.
- **Frontend** : page `/compare` façon `ScanPage` — tableau multi-variant
  (colonnes : label, émission, K, log-lik, BIC, AIC, HQIC, status), badges
  « best by BIC/AIC/HQIC », lien view → /results/{job}.
- Nav : entrée « Compare » dans `Layout.tsx`.

### Comparabilité dans l'UI/CLI/Python
- Le champ `comparable` + `note` portés partout.
- `best_by_*` ne considère que `comparable=True`. Si la grille web n'a que
  des comparables (cas v1), pas de complication.

## 4. Scope boundaries (ce qu'on ne fait PAS)

- **PAS de cross-paradigme** (SARIMAX / UCM / rSLDS). Rejeté — hors
  HMM-land (scope discipline, cf. rejet rSLDS 2026-05-27).
- **PAS de sélection auto des covariables NHMM** — l'utilisateur fournit
  les `Z`. (La sélection causale Granger/TE de Robin = spec futur distinct.)
- **Web UI v1 = grille comparable seulement**. NHMM/Factorial comparison
  reste Python/CLI. (Évite l'UI complexe de covariables-par-candidat.)
- **PAS de model averaging / ensembling** — on sélectionne, on ne combine
  pas. (BMA = sujet séparé si demandé.)
- **PAS de cross-validation out-of-sample** en v1 — le ranking est par
  critère d'information in-sample (BIC/AIC/HQIC). CV temporelle =
  amélioration future possible (la recherche Nathan a un `best_alpha`
  TimeSeriesSplit, mais c'est pour rSLDS, hors scope).

## 5. Tests

### Phase 1 (`tests/test_selection.py`)
| Test | Vérifie |
|---|---|
| `test_compare_ranks_comparable_by_bic` | grille gaussienne K=2..4 → ranking BIC correct |
| `test_best_only_among_comparable` | NHMM ajouté → jamais élu best, comparables le sont |
| `test_nhmm_flagged_not_comparable` | `comparable=False` + note sur le candidat NHMM |
| `test_factorial_flagged_not_comparable` | idem Factorial |
| `test_auto_grid_generates_emission_x_k` | `auto_grid` produit le bon nombre/forme de candidats |
| `test_failed_candidate_excluded_not_fatal` | un fit qui lève → exclu, comparaison continue |
| `test_repr_html_marks_noncomparable` | `_repr_html_` contient un marqueur ⚠ sur non-comparables |
| `test_to_summary_dict_shape` | dict sérialisable JSON avec tous les candidats |

### Phase 2 (`tests/test_cli.py` additions)
| Test | Vérifie |
|---|---|
| `test_compare_cli_ranks_dir` | `hmm-fit compare` sur un dir de topologies → table, exit 0 |
| `test_compare_cli_no_candidates_exits_nonzero` | dir vide → exit ≠ 0, message clair |

### Phase 3 (`tests/studio/test_endpoints.py` + e2e)
| Test | Vérifie |
|---|---|
| `test_compare_start_and_status` | endpoint parent/child, best-by-criterion peuplé |
| `test_compare_grid_generation` | k_range + emission_types → bonne grille de children |
| (e2e Playwright, optionnel) | page /compare affiche le tableau + badges |

## 6. Définition de "done" (par phase)

**Phase 1** :
- [ ] `hmm_core/selection.py` : `compare_models`, `auto_grid`,
      `CandidateResult`, `ModelComparison` (+ `_repr_html_`), exportés top-level.
- [ ] 8 tests Phase 1 verts.

**Phase 2** :
- [ ] `hmm-fit compare` dans la CLI (`hmm_core/cli.py`).
- [ ] 2 tests CLI verts.

**Phase 3** :
- [ ] `POST /api/compare/start` + `GET /api/compare/{id}` + schemas.
- [ ] page `/compare` frontend + nav + client.ts.
- [ ] 2 tests endpoints verts ; bundle rebuilt ; tsc clean.

**Transversal** :
- [ ] CHANGELOG `[Unreleased]` mis à jour.
- [ ] (Optionnel) leçon Academy 14 « Choosing the right model » + biblio.

## 7. Open questions (à résoudre avant/pendant le plan)

1. **Format `grid.yaml` du CLI** : à figer (schéma : `base`, `k_range`,
   `emission_types`, `n_mix`). Décidé à l'impl Phase 2.
2. **Persistance du `CompareResult` web** : réutilise-t-on la table de jobs
   K-scan telle quelle (un parent « compare » avec children hétérogènes) ou
   un nouveau type de parent ? Préférence : réutiliser, avec un champ
   `kind` par child. À confirmer en lisant `jobs.py` au début de Phase 3.
3. **Leçon Academy 14** : optionnelle, déférée si elle ajoute du risque.

## 8. Provenance

- `Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/ModelFinder.ipynb`
  (`Model_Selection`, `Compute_HQIC_model`) — la part HMM-only inspire ce
  spec. La part cross-paradigme (SARIMAX/UCM/rSLDS) est explicitement
  exclue (§ 4).
