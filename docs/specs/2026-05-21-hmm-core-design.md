# Design — `hmm-core` (sous-projet A de `hmm-studio`)

**Date** : 2026-05-21
**Auteur** : Robin Denis (brainstorm avec Claude Code)
**Status** : Draft, en attente de revue utilisateur

## Contexte

Le projet `Experiment.Crypto.2026S1.RobinDenis` contient déjà un dashboard HMM
opérationnel (`src/cmex_crypto/viz/hmm_dashboard/`) — Dash + hmmlearn, K-scan
BIC/AIC, NHMM, auto-labels, anchors, etc. Le dashboard *consomme* un modèle
HMM ergodique (transitions libres) et affiche tout ce qu'on peut afficher.

Ce qui manque pour réellement "configurer" un HMM avant fit :

1. **Définir une topologie structurée** : interdire certaines transitions
   (Bakis, left-right, branches…) au lieu de partir ergodique complet.
2. **Fit contraint** : Baum-Welch respectant ces interdictions à chaque
   itération.
3. **Stratégies d'initialisation** configurables (pas seulement le seed
   hardcodé du dashboard actuel).
4. **Outil agnostique** : la stack actuelle assume OHLCV crypto. Pour servir
   d'autres usages (séries quelconques, données catégorielles, comptages
   Poisson), il faut un cœur découplé.

## Objectif

Construire `hmm-core` : un package Python pur (zéro UI, zéro Dash, zéro
matplotlib) qui :

- Charge une topologie HMM déclarée en YAML.
- Fit le modèle via Baum-Welch contraint (matrice de transition `A` masquée).
- Supporte les 4 émissions de la famille `hmmlearn` (Gaussian, GMM,
  Multinomial, Poisson).
- Expose CLI + API Python utilisables depuis n'importe quel projet.

Le futur sous-projet B (`hmm-studio` — éditeur node-graph web) générera ces
fichiers YAML depuis une UI ; A doit être conçu pour cet usage en aval.

**Hors scope explicite de ce spec** :

- UI web (éditeur node-based, dashboard, upload navigateur) → sous-projet B
- Visualisations interactives (heatmaps live, animations transitions) → B/C
- Migration du dashboard `cmex_crypto` existant vers `hmm-core` → décision
  séparée, post-MVP
- NHMM contraint (transitions covariate-dependent + masque) → post-MVP
- Émissions custom utilisateur (Student-T, etc. hors famille hmmlearn) → YAGNI

## Décisions actées pendant le brainstorm

| Décision | Choix | Alternative écartée |
|---|---|---|
| Scope global | Outil HMM généraliste séparé, dans un nouveau repo `Tools/hmm_studio/` | Extension du dashboard existant (rejetée : couple trop fort à crypto) |
| Premier sous-projet | `hmm-core` (engine Python pur, pas d'UI) | MVP web (rejeté : repousse la validation du point dur — fit contraint) |
| Localisation repo | `C:\Users\rdenis\VScode\Tools\hmm_studio\` (repo standalone, git séparé) | Vendoré sous `Experiment.Crypto.2026S1.RobinDenis/` (rejeté : compromet la généralité) |
| Backend de fit | `hmmlearn` sous-classé avec masque sur `_do_mstep` | `pomegranate` (rupture avec dashboard existant) ; wrapper hybride (over-engineering) |
| Émissions supportées | Famille complète : Gaussian, GMM, Multinomial, Poisson | Gaussian-only (trop restrictif vu l'ambition généraliste) |
| Format topology | YAML, `allowed_transitions` (edges autorisés, omission = ergodique complet) | JSON (moins lisible) ; `forbidden_transitions` (moins explicite) |

## Architecture

### Layout repo

```
Tools/hmm_studio/                            # nouveau repo standalone
├── pyproject.toml                           # editable install, name="hmm-studio"
├── README.md
├── .gitignore                               # venv, __pycache__, results/, .pytest_cache
├── docs/
│   └── specs/
│       └── 2026-05-21-hmm-core-design.md    # ce fichier
├── src/
│   └── hmm_core/                            # ← package A
│       ├── __init__.py
│       ├── topology.py                      # Topology, TopologyValidator
│       ├── constraints.py                   # mask helpers (sparse-friendly)
│       ├── distributions.py                 # EmissionSpec union type
│       ├── init.py                          # init strategies
│       ├── io.py                            # YAML load, pickle save, JSON summaries
│       ├── cli.py                           # entry point `hmm-fit`
│       └── fit/
│           ├── __init__.py                  # public `fit()` dispatcher
│           ├── _base.py                     # _apply_mask, shared utilities
│           ├── gaussian.py                  # ConstrainedGaussianHMM
│           ├── gmm.py                       # ConstrainedGMMHMM
│           ├── multinomial.py               # ConstrainedMultinomialHMM
│           └── poisson.py                   # ConstrainedPoissonHMM
└── tests/
    ├── conftest.py                          # fixtures (datasets synthétiques)
    ├── test_topology.py
    ├── test_constraints_gaussian.py
    ├── test_constraints_gmm.py
    ├── test_constraints_multinomial.py
    ├── test_constraints_poisson.py
    ├── test_init_strategies.py
    ├── test_io_roundtrip.py
    └── test_cli.py
```

### Dépendances (`pyproject.toml`)

Runtime : `numpy`, `pandas`, `hmmlearn>=0.3,<0.4` (épingle stricte, cf.
risque 1 plus bas), `scikit-learn` (pour kmeans init), `pyyaml`, `typer`.
Dev/test : `pytest`, `pytest-cov`, `hypothesis` (optionnel pour property
tests sur `_apply_mask`), `ruff`, `black`.

Pas de Plotly, pas de Dash, pas de matplotlib. Le package reste consommable
depuis n'importe quel contexte (notebook, CLI, futur backend web).

### Modules — responsabilités

**`topology.py`** — déclaration immuable de la structure du modèle.

```python
@dataclass(frozen=True)
class EmissionSpec:
    type: Literal["gaussian", "gmm", "multinomial", "poisson"]
    n_features: int | None = None          # gaussian, gmm
    covariance_type: str | None = None     # gaussian, gmm : full/diag/tied/spherical
    n_mix: int | None = None               # gmm
    n_symbols: int | None = None           # multinomial

@dataclass(frozen=True)
class InitSpec:
    strategy: Literal["uniform", "random", "kmeans", "data_frequencies"]
    seed: int

@dataclass(frozen=True)
class FitSpec:
    algorithm: Literal["baum_welch"]
    n_iter: int
    tol: float

@dataclass(frozen=True)
class Topology:
    name: str
    n_states: int
    state_names: list[str]
    emission: EmissionSpec
    allowed_transitions: list[tuple[str, str]] | None    # None = ergodic complet
    startprob: str | list[float]                          # "uniform" | "first_state" | floats
    init: InitSpec
    fit: FitSpec

    @classmethod
    def from_yaml(cls, path: Path) -> "Topology": ...

    def transition_mask(self) -> np.ndarray:
        """K x K bool — True si edge autorise, False si force a 0."""
        ...

    def validate(self) -> None:
        """Leve TopologyError si incoherent (n_states != len(state_names), etat
        inconnu dans allowed_transitions, n_features manquant pour gaussian,
        etc.)"""
        ...
```

**`constraints.py`** — utilitaires pour manipuler les masques. Initial scope
minimal : conversion `(state_names, allowed_transitions) -> mask`. Réservé
pour des helpers plus avancés (détection états absorbants, états orphelins,
analyse de la sparsité) si besoin émerge.

**`distributions.py`** — méthodes sur `EmissionSpec` qui mappent vers les
arguments hmmlearn (paramètres de classe, `init_params`, `params`). Centralise
la connaissance "comment hmmlearn veut être appelé pour ce type d'émission".

**`init.py`** — stratégies d'initialisation. Chaque fonction respecte le
masque (zéros forcés là où interdit) avant de retourner.

```python
def transmat(topology: Topology, *, seed: int, X: np.ndarray | None = None) -> np.ndarray:
    """Retourne A initial respectant topology.transition_mask().

    - uniform           : 1 / count(allowed) par ligne, X ignore.
    - random            : Dirichlet(alpha=1) sur allowed, X ignore.
    - kmeans            : A reste uniforme (kmeans n'agit que sur les emissions).
    - data_frequencies  : pre-cluster X par kmeans (k=K), frequences observees
                          des sequences de cluster ; necessite X.
    """

def startprob(topology: Topology, *, seed: int) -> np.ndarray:
    """Retourne pi initial selon topology.startprob."""

def emission_params(topology: Topology, X: np.ndarray | None, *, seed: int) -> dict:
    """Retourne dict {means_, covars_, weights_, emissionprob_, ...} a pre-poser
    avant model.fit(). Sortie depend de emission.type et init.strategy.
    Pour kmeans: means = centroides, covars = covariances empiriques par cluster."""
```

**`fit/_base.py`** — fonction `_apply_mask` partagée par les 4 sous-classes.

```python
def _apply_mask(transmat: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """transmat * mask + renormalisation par ligne.

    Garantit:
      - transmat[i, j] == 0 partout ou mask[i, j] est False (apres retour)
      - transmat.sum(axis=1) ≈ 1 sur toutes les lignes (atol 1e-12)
      - Ligne entierement zero apres masquage -> uniform sur allowed edges
        de cette ligne (fallback de securite, ne devrait survenir que pour
        des etats absorbants interdits, lance un warning).
    """
```

**`fit/gaussian.py`** (et identique en structure pour les 3 autres) :

```python
class ConstrainedGaussianHMM(GaussianHMM):
    def __init__(self, *args, transmat_mask: np.ndarray | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transmat_mask = transmat_mask

    def _do_mstep(self, stats):
        super()._do_mstep(stats)
        if self.transmat_mask is not None:
            self.transmat_ = _apply_mask(self.transmat_, self.transmat_mask)
```

Trois jumelles : `ConstrainedGMMHMM(GMMHMM)`, `ConstrainedMultinomialHMM(MultinomialHMM)`,
`ConstrainedPoissonHMM(PoissonHMM)`. Toutes overrident le **même** point
(`_do_mstep` post-call) ; on ne touche jamais au calcul EM en amont.

**`fit/__init__.py`** — dispatcher public.

```python
@dataclass(frozen=True)
class FittedModel:
    model: object                  # ConstrainedXHMM instance
    topology: Topology
    log_likelihood: float
    bic: float
    aic: float
    n_iter_actual: int
    converged: bool
    seed: int

def fit(topology: Topology, X: np.ndarray, *, seed: int | None = None) -> FittedModel:
    """Fit le modele decrit par `topology` sur `X`.

    Etapes:
      1. topology.validate() -> raise sur incoherence.
      2. mask = topology.transition_mask()
      3. initial_A = init.transmat(topology, seed=seed, X=X)
      4. initial_pi = init.startprob(topology, seed=seed)
      5. emission_kwargs = init.emission_params(topology, X, seed=seed)
      6. cls = {gaussian: ConstrainedGaussianHMM, ...}[topology.emission.type]
      7. model = cls(n_components=K, transmat_mask=mask,
                     init_params=<sans 't' ni params pre-poses>,
                     params=<tout apprenable>,
                     n_iter=..., tol=..., random_state=seed,
                     **emission_kwargs_hmmlearn_signature)
      8. model.transmat_ = initial_A   # pre-poses, init_params les exclut
      9. model.startprob_ = initial_pi
      10. for k, v in emission_kwargs.items(): setattr(model, k, v)
      11. model.fit(X)
      12. Construire FittedModel avec log_lik, BIC, AIC calcules.
    """
```

**`io.py`** — load YAML topology, save pickle modèle, save JSON summary.

```python
def load_topology(path: Path) -> Topology: ...
def save_model(fitted: FittedModel, output_dir: Path) -> None:
    """Ecrit output_dir/{model.pkl, summary.json, fit_log.txt}.

    summary.json contient :
      - topology (round-tripped)
      - log_likelihood, bic, aic
      - n_iter_actual, converged
      - mask_violation_norm: float (sanity : (transmat * (1-mask)).sum())
      - seed, hmmlearn_version
      - duration_seconds
    """
def load_model(path: Path) -> FittedModel: ...
def save_decoded(viterbi: np.ndarray, posterior: np.ndarray, index: pd.Index,
                 output: Path) -> None:
    """Ecrit parquet : index + viterbi + posterior_state_0..K."""
```

Pickle est pinné à la version `hmmlearn` au moment du save (stocké dans
`summary.json`). `load_model` warne si version mismatch.

**`cli.py`** — interface Typer.

```bash
hmm-fit validate <topology.yaml>
hmm-fit run <topology.yaml> <data.csv> --output <dir> [--seed N]
hmm-fit decode <model.pkl> <data.csv> --output <decoded.parquet>
hmm-fit show <model.pkl>
```

`run` lit `data.csv` (headers = noms de features, ordre doit matcher
`emission.n_features` pour Gaussian/GMM ; une colonne `value` pour
Multinomial/Poisson), valide la topology, fit, écrit le bundle de sortie.

### Format de fichier — topology YAML

```yaml
name: crypto_4_state_left_right
n_states: 4
state_names: [calm, trend_up, vol, crash]

emission:
  type: gaussian          # gaussian | gmm | multinomial | poisson
  covariance_type: full   # gaussian/gmm : full | diag | tied | spherical
  n_features: 3           # gaussian/gmm : dimension obs
  n_mix: 1                # gmm : nombre de composantes par etat
  n_symbols: null         # multinomial : taille du vocabulaire

allowed_transitions:
  - [calm, calm]
  - [calm, trend_up]
  - [trend_up, trend_up]
  - [trend_up, vol]
  - [vol, vol]
  - [vol, crash]
  - [vol, calm]
  - [crash, crash]
  - [crash, calm]
# Omission de allowed_transitions => ergodique complet (tout autorise).

startprob: uniform        # "uniform" | "first_state" | [0.7, 0.1, 0.1, 0.1]

init:
  strategy: kmeans        # uniform | random | kmeans | data_frequencies
  seed: 42

fit:
  algorithm: baum_welch
  n_iter: 200
  tol: 1e-4
```

### Format de fichier — `summary.json`

```json
{
  "schema_version": 1,
  "topology": { "...": "round-tripped Topology" },
  "fit": {
    "log_likelihood": -3421.7,
    "bic": 6987.4,
    "aic": 6889.1,
    "n_iter_actual": 47,
    "converged": true,
    "mask_violation_norm": 1.2e-14
  },
  "runtime": {
    "seed": 42,
    "hmmlearn_version": "0.3.2",
    "hmm_core_version": "0.1.0",
    "duration_seconds": 3.7
  }
}
```

`mask_violation_norm` doit être `< 1e-10` pour qu'un fit soit accepté ; au-
dessus, l'écriture du summary lève une exception (sanity check : si une
sous-classe contrainte oublie d'appliquer le masque, on s'en rend compte
immédiatement, pas trois semaines plus tard).

## Stratégies d'initialisation — détail

| Stratégie | Initial `A` | Initial `pi` | Initial émissions |
|---|---|---|---|
| `uniform` | `1/count(allowed)` par ligne sur edges autorisés | selon `startprob` field | hmmlearn defaults |
| `random` | Dirichlet(α=1) sur edges autorisés | selon `startprob` field | `random_state=seed` |
| `kmeans` | comme `uniform` | comme `uniform` | Gaussian/GMM : `means` = centroïdes k-means sur X, `covars` = covariances empiriques par cluster. Poisson : `lambdas` = moyenne par cluster. Multinomial : kmeans non-pertinent → retombe sur `emissionprob` empirique global (`np.bincount(X) / len(X)` répété K fois) + warning. |
| `data_frequencies` | Pré-cluster X par kmeans (k=K), comptage masqué des transitions cluster `(c_t, c_{t+1})` + normalisation. Pour Multinomial : groupes par valeur d'observation modulo K (heuristique de bas niveau) + warning. | Fréquences empiriques du premier cluster | comme `kmeans` |

Toutes les stratégies retournent une matrice `A` qui respecte déjà le masque
par construction (les valeurs sont assignées uniquement aux entrées
autorisées). Un appel final à `_apply_mask` est utilisé comme garde-fou
(coût négligeable, attrape les bugs de stratégie).

## Tests — couverture détaillée

### `test_topology.py`
- Parsing YAML valide → `Topology` correct, round-trip YAML.
- Parsing YAML invalide (n_states ≠ len(state_names), état inconnu dans
  `allowed_transitions`, n_features manquant pour Gaussian, n_symbols
  manquant pour Multinomial) → `TopologyError`.
- `transition_mask()` produit la bonne matrice booléenne.
- Omission de `allowed_transitions` → mask tout-à-True.

### `test_constraints_<emission>.py` (×4, un par émission)
- Fit sur dataset synthétique avec masque restrictif (left-right K=3).
- Après fit : `(model.transmat_ * (1 - mask)).sum() < 1e-10`.
- Après fit : `model.transmat_.sum(axis=1) ≈ 1` pour toutes les lignes.
- Fit avec `mask=None` → résultat numériquement identique à la classe
  vanilla `hmmlearn.hmm.GaussianHMM` (etc.) sur même seed + même init →
  test de non-régression critique.
- État absorbant interdit (toute la ligne masquée) → fallback uniform sur
  allowed + warning émis (test capture le warning).

### `test_init_strategies.py`
- Chaque stratégie retourne un `A` respectant le masque.
- Déterminisme avec seed fixe.
- `kmeans` / `data_frequencies` lèvent si `X is None`.

### `test_io_roundtrip.py`
- `load_topology(save_topology(t)) == t` (égalité dataclass).
- `load_model(save_model(m, dir)).model.transmat_ ≈ m.model.transmat_`.
- `summary.json` contient toutes les clés attendues.

### `test_cli.py`
- `hmm-fit validate topology.yaml` → exit 0 sur valid, exit 1 + message
  utile sur invalid.
- `hmm-fit run topology.yaml data.csv -o tmp/` → écrit les 3 fichiers, exit 0.
- `hmm-fit decode model.pkl data.csv -o out.parquet` → parquet a les bonnes
  dimensions (T × (1+K)).
- `hmm-fit show model.pkl` → stdout contient log_lik, BIC, n_states, mask
  rendering ASCII.

### Fixtures (`conftest.py`)
- `synthetic_gaussian_4state` : dataset Gaussian K=4 D=3 N=1000, seed fixe,
  topology left-right pré-écrite.
- `synthetic_gmm_3state` : K=3, n_mix=2.
- `synthetic_multinomial_5symbol` : K=3, vocab=5.
- `synthetic_poisson_3state` : K=3, lambdas distincts par état.

Property tests optionnels (`hypothesis`) :
- Pour toute matrice non-négative et tout masque binaire compatible,
  `_apply_mask` produit une matrice satisfaisant les deux invariants
  (zéros sur masque, lignes sommant à 1).

## Risques identifiés

1. **hmmlearn `_do_mstep` peut changer entre versions** — c'est une méthode
   semi-privée. Mitigation : épingler `hmmlearn>=0.3,<0.4` dans
   `pyproject.toml`, test de non-régression vs vanilla à chaque émission,
   re-tester quand on monte la borne supérieure.
2. **GMMHMM, MultinomialHMM, PoissonHMM** ont des signatures de `_do_mstep`
   subtilement différentes (ce que `stats` contient diffère). Le contournement
   "post-call multiplier-by-mask" reste valide tant qu'on touche que
   `self.transmat_` après — vérifié par les 4 tests dédiés.
3. **États absorbants interdits** (e.g. mask qui interdit toutes les sorties
   d'un état) sont mal-définis pour Baum-Welch. Choix : fallback uniform +
   warning. Alternative possible : `TopologyError` à la validation. Décision :
   warner pour ne pas bloquer les cas-limites (ex: état atteint puis jamais
   re-visité). À reconsidérer si le warning passe inaperçu en pratique.
4. **Multinomial avec `n_symbols` mal-spécifié** vs `data.csv` → erreur
   hmmlearn opaque. Mitigation : `Topology.validate(X)` vérifie que
   `X.max() < n_symbols` avant fit.
5. **Pickle inter-version hmmlearn** — risque connu. Mitigation : warning à
   load, recommander re-fit si version mismatch.

## Critères de "done" pour le sous-projet A

- `pip install -e Tools/hmm_studio` réussit dans un venv neuf.
- `pytest tests/` passe (couverture >= 85% sur `src/hmm_core/`).
- `hmm-fit run examples/topology_left_right.yaml examples/data_gaussian.csv -o /tmp/out/`
  produit un bundle valide.
- README contient : install, un exemple Gaussian, un exemple Multinomial,
  un schéma YAML annoté.
- ADR (à créer pendant l'implémentation, `docs/decisions/0001-backend-hmmlearn-patch.md`)
  actant le choix `hmmlearn` sous-classé vs `pomegranate` ; reprend les
  arguments du brainstorm 2026-05-21.

## Étapes ultérieures (hors scope de ce spec)

- **Sous-projet B** : `hmm-studio` web (FastAPI + React Flow). Génère des
  YAML topology depuis une UI node-graph. Lance fit via subprocess `hmm-fit
  run` ou via API Python directe.
- **Sous-projet C** : visualisations avancées (NHMM breathing, replay
  temporel, export figures publication-ready).
- **Migration optionnelle** du dashboard `cmex_crypto` actuel pour consommer
  `hmm_core` (remplace le `fit_hmm` interne). Décision à prendre quand A est
  stable.
