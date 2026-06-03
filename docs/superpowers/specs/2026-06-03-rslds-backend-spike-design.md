---
Status: current
---

# rSLDS backend for hmm_studio — spike v0 design

*Spec écrite le 2026-06-03. Sous-projet **D** de la réutilisation du travail de
Nathan dans hmm_studio (voir le découpage A/B/C/D dans le projet voisin
`Experiment.Crypto.2026S1.NathanBerbinau`). A (re-benchmark) livré, B (leçons
Academy 14+15) et C (option dcor) mergées sur main 2026-06-03.*

## 1. Contexte / problème

hmm_studio aujourd'hui fournit, via son backend protocol
(`hmm_core.backends._protocol.HMMBackend`) deux implémentations enregistrées :
`hmmlearn` (défaut, frequentiste) et `bayesian` (optionnel via PyMC). Ces deux
implémentations partagent l'hypothèse fondamentale du HMM : *états discrets +
émission gaussienne/GMM/multinomiale/Poisson par état + transitions K×K
homogènes*.

Le travail de Nathan (`Projet_Robin/ssm_extensions.py`) ajoute deux concepts
qu'aucun backend hmm_studio ne couvre :
- **Émission Skew-T** — abandonnée empiriquement par A (sous-performe Student-T).
  Pas dans le scope de D.
- **rSLDS (recurrent Switching Linear Dynamical System)** — modèle à *latent
  continu commutant* : par régime k, l'état latent `x_t = A_k x_{t-1} + b_k +
  bruit`, les transitions discrètes `z_t` dépendent de `x_{t-1}` (recurrent), et
  l'observation `y_t = C x_t + d + bruit`. Capture la dynamique *intra-régime*
  qu'aucun HMM standard ne modélise. C'est précisément la lacune de hmm_studio
  identifiée dans `[[hmm-studio-overlaps-nathan-work]]`.

Le re-benchmark de A a établi :
- Les HMM gaussiens s'effondrent sur la queue lourde des features ETH (LL hold-out
  −200 à −400, variance énorme).
- Student-T HMM bat tout (LL ≈ −6.3) ; NHMM n'ajoute rien.
- Le rSLDS n'est PAS comparable à la famille HMM sur la LL marginale (intractable
  pour SLDS) — mais il modélise une chose que les HMM ne modélisent pas
  (dynamique latente continue).

Donc l'intérêt de rSLDS dans hmm_studio n'est pas « battre les HMM sur la LL »
mais **offrir un nouveau type de modèle** (latent continu commutant) que
l'utilisateur peut entraîner et inspecter quand sa donnée a une structure de
dynamique linéaire par régime.

Deux contraintes connues bloquent l'implémentation immédiate :
1. **ssm ne compile pas sur Windows sans MSVC**. La politique Enterprise du poste
   bloque l'install des C++ Build Tools (winget 1602 ×2 dans A). Docker est
   l'unique chemin reproductible. Précédent établi par A
   (`Projet_Robin/benchmark/Dockerfile`).
2. **Le code aval de hmm_studio by-passe le protocole backend** : `io.save_model`,
   `_repr_html_`, NHMM, et probablement d'autres lisent `.transmat_`,
   `.predict()`, `.monitor_.history` directement sur `FittedModel.model` à la
   façon hmmlearn. Un objet rSLDS qui n'expose pas ces attributs casse ces
   consommateurs. Risque #1 de l'audit d'exploration.

## 2. Objectif

Livrer un **spike** v0 d'un backend rSLDS qui :
1. Conforme formellement le protocole `HMMBackend` existant (`fit`,
   `fit_supervised`, `decode`, `predict_proba`, `score`, retour
   `BackendFitResult`).
2. Reste utilisable malgré le by-pass downstream, grâce à un *adapter* qui expose
   sur l'objet `model` retourné les attributs duck-type façon hmmlearn
   (`.transmat_`, `.startprob_`, `.predict()`, `.predict_proba()`, `.score()`,
   `.monitor_.history`, `.monitor_.converged`), chacun documentant sa sémantique
   rSLDS-spécifique.
3. S'install via `pip install hmm-studio[rslds]` (extra optionnel, pattern
   `[bayesian]`) — pour les contributeurs Linux/Mac avec gcc — OU via le
   Dockerfile porté de A — obligatoire pour le poste Windows actuel.
4. Soit **testé** localement via `pytest.importorskip("ssm")` (saute proprement
   si extra absent) + `@pytest.mark.slow` sur le tier coûteux, et vérifié en CI
   manuellement (`workflow_dispatch`) dans un job Docker.
5. N'expose rien dans l'UI (Wizard, ComparePage). Documenté « drop to CLI /
   notebook ».

Succès = un utilisateur Linux/Mac peut faire
```python
from hmm_core.fit import fit
result = fit(topology, X, backend="rslds")
print(result.log_likelihood, result.transmat)
```
après `pip install "hmm-studio[rslds]"`, et un utilisateur Windows peut faire la
même chose dans le conteneur Docker porté de A.

## 3. Design

### 3.1 Module structure

```
src/hmm_core/backends/
├── _protocol.py             (existant — pas touché)
├── _registry.py             (existant — pas touché)
├── __init__.py              (MODIFIÉ — registration rSLDS gated try/except)
├── hmmlearn_backend.py      (existant — pas touché)
├── bayesian_backend.py      (existant — pas touché)
└── rslds_backend.py         (NEW — RSLDSBackend + RSLDSFittedBundle + _ElasticNetRSLDSCompat)

tools/docker/
└── rslds.Dockerfile         (NEW — port verbatim de Projet_Robin/benchmark/Dockerfile)

tests/
├── test_rslds_backend_smoke.py  (NEW — fast tier, sans @slow)
└── test_rslds_backend.py        (NEW — full tier, avec @slow)

.github/workflows/
└── rslds-docker.yml         (NEW — workflow_dispatch + hebdo cron optionnel)
```

Plus `pyproject.toml` modifié pour ajouter l'extra `[rslds]`.

### 3.2 `RSLDSBackend(HMMBackend)` — protocole stateless

```python
class RSLDSBackend:
    name = "rslds"

    def __init__(self, regularize: str = "none") -> None:
        if regularize not in {"none", "elastic_net"}:
            raise ValueError(f"regularize must be 'none' or 'elastic_net', got {regularize!r}")
        self.regularize = regularize

    def fit(self, topology, X, *, seed, lengths=None, initial_transmat, initial_startprob,
            emission_kwargs, mask, progress_callback=None, transmat_prior=None) -> BackendFitResult:
        ...

    def fit_supervised(self, topology, X, states, *, seed, lengths=None, mask) -> BackendFitResult:
        raise NotImplementedError(
            "rslds backend does not yet support fit_supervised "
            "(spike v0; tracked for v0.1)"
        )

    def decode(self, model, X, lengths=None) -> np.ndarray:
        ...

    def predict_proba(self, model, X, lengths=None) -> np.ndarray:
        ...

    def score(self, model, X, lengths=None) -> float:
        ...
```

**Comportement de `fit`** :
1. Importer `ssm` localement.
2. Calculer `K = topology.n_states`, `n_features = X.shape[1]`,
   `D_latent = max(1, min(K, n_features - 1))` (contrainte stricte de ssm pour
   les émissions orthogonales : `N > D`).
3. Si `self.regularize == "none"` : `model = ssm.SLDS(N=n_features, K=K,
   D=D_latent, transitions="recurrent_only")`.
4. Sinon : `model = _ElasticNetRSLDSCompat(N=n_features, K=K, D=D_latent,
   alpha=0.05, l1_ratio=0.5, transitions="recurrent_only")` (le shim ; voir
   §3.4).
5. `q = ssm.variational.SLDSStructuredMeanFieldVariationalPosterior(model, X)`.
6. `np.random.seed(seed)` ; `elbos = model.fit(X, variational_posterior=q,
   method="laplace_em", num_iters=topology.fit.n_iter or 50)`.
7. Construire `bundle = RSLDSFittedBundle(model=model, q_train=q, D_latent=D_latent,
   regularize=self.regularize, n_features=n_features, K=K, elbo_history=list(elbos))`.
8. Calculer `transmat_post = bundle.transmat_` (posterior mean discrete transitions
   moyennes sur les pas de q_train), `startprob_post = bundle.startprob_`.
9. `converged` = `True` si la pente des 3 derniers ELBO est < 1e-3 en valeur
   absolue relative, sinon `False`. Pas d'exception sur non-convergence.
10. Retourner :
    ```python
    BackendFitResult(
        model=bundle,
        transmat=transmat_post,
        startprob=startprob_post,
        log_likelihood=float(elbos[-1]),   # ELBO, NOT marginal LL (caveat documenté)
        n_iter_actual=len(elbos),
        converged=converged,
    )
    ```

**`decode`** : `q_X = ssm.variational.SLDSStructuredMeanFieldVariationalPosterior(model, X) ; model._fit_laplace_em(q_X, [X], inputs, masks, tags, num_iters=10, learning=False) ; return q_X.mean_discrete_states[0].argmax(axis=1)` (réutilise le pattern de A's `rslds_predictive_metrics`).

**`predict_proba`** : même chose mais retourne `q_X.mean_discrete_states[0]`
shape `(T, K)`.

**`score`** : retourne l'ELBO final de `_fit_laplace_em` sur X (E-step seule).
**Documenté en docstring : « NOT a marginal log-likelihood. ELBO is a lower bound.
Not directly comparable to hmmlearn `score()`. Use only for relative comparison
between rSLDS fits of the same topology. »**

`mask`, `initial_transmat`, `initial_startprob`, `emission_kwargs`,
`progress_callback`, `transmat_prior` : pour le spike v0, **silencieusement
ignorés** ; la docstring les liste explicitement comme « accepted-for-protocol-
conformance, not currently honoured by rSLDS (recurrent transitions and
continuous latent are different concepts) ». Pas de `warnings.warn()` à
l'exécution (resterait bruyant à chaque fit). Ils restent dans la signature
pour conformer le protocole.

### 3.3 `RSLDSFittedBundle` — adapter bi-face

```python
@dataclass(frozen=True)
class RSLDSFittedBundle:
    """Wraps a fitted rSLDS model, exposing both rSLDS-native and hmmlearn-shaped
    attributes so downstream code that bypasses the formal backend protocol
    (io.save_model, _repr_html_, NHMM, ComparePage) continues to function.

    All hmmlearn-shaped attributes (transmat_, startprob_, predict, score, ...)
    are computed on demand from the underlying ssm posterior and DOCUMENT their
    rSLDS-specific semantics in their docstrings."""

    model: Any                 # the underlying ssm.SLDS or _ElasticNetRSLDSCompat
    q_train: Any               # SLDSStructuredMeanFieldVariationalPosterior on X_train
    D_latent: int
    regularize: str
    n_features: int
    K: int
    elbo_history: list[float]

    # ---- rSLDS-native surface ----
    @property
    def dynamics_As(self) -> np.ndarray:
        """Per-regime dynamics matrices, shape (K, D_latent, D_latent)."""
        return np.asarray(self.model.dynamics.As)

    @property
    def dynamics_bs(self) -> np.ndarray:
        """Per-regime affine offsets, shape (K, D_latent)."""
        return np.asarray(self.model.dynamics.bs)

    @property
    def emissions_Cs(self) -> np.ndarray:
        """Emission projection matrix, shape (n_features, D_latent)."""
        return np.asarray(self.model.emissions.Cs[0])

    @property
    def emissions_ds(self) -> np.ndarray:
        """Emission offset, shape (n_features,)."""
        return np.asarray(self.model.emissions.ds[0])

    @property
    def latent_states(self) -> np.ndarray:
        """Mean continuous latent trajectory from q_train, shape (T_train, D_latent)."""
        return np.asarray(self.q_train.mean_continuous_states[0])

    # ---- hmmlearn-shaped duck-type surface (with documented rSLDS semantics) ----
    @property
    def transmat_(self) -> np.ndarray:
        """(K, K) posterior-mean discrete transition matrix over q_train timesteps.

        rSLDS uses RECURRENT transitions: the true transition matrix is
        time-varying and depends on x_{t-1}. This property returns the
        time-averaged posterior of those transitions — a USABLE summary but
        NOT a stationary transition matrix in the HMM sense. Use only for
        broad-stroke inspection."""
        Ez_zp1 = self.q_train.discrete_expectations  # list of (Ez, Ezzp1, normalizer)
        Ezzp1_mean = np.mean([t[1] for t in Ez_zp1], axis=(0, 1))  # (K, K)
        Ezzp1_mean = Ezzp1_mean / Ezzp1_mean.sum(axis=1, keepdims=True)
        return Ezzp1_mean

    @property
    def startprob_(self) -> np.ndarray:
        """(K,) posterior-mean initial-state distribution from q_train."""
        Ez = self.q_train.discrete_expectations[0][0]  # (T, K)
        return Ez[0]

    def predict(self, X: np.ndarray, lengths=None) -> np.ndarray:
        """Viterbi-style decode = argmax of E-step posterior on X. See backend.decode."""
        from hmm_core.backends.rslds_backend import RSLDSBackend
        return RSLDSBackend._decode_static(self, X)

    def predict_proba(self, X: np.ndarray, lengths=None) -> np.ndarray:
        """(T, K) posterior over discrete states from E-step inference on X."""
        from hmm_core.backends.rslds_backend import RSLDSBackend
        return RSLDSBackend._predict_proba_static(self, X)

    def score(self, X: np.ndarray, lengths=None) -> float:
        """ELBO on X via E-step-only inference. **NOT a marginal log-likelihood**.

        rSLDS marginal likelihood is intractable; we return the ELBO, which is a
        variational lower bound. Do NOT compare across backends (the hmmlearn
        score() returns the exact marginal LL). Use only for relative
        comparison between rSLDS fits with the same topology."""
        from hmm_core.backends.rslds_backend import RSLDSBackend
        return RSLDSBackend._score_static(self, X)

    @property
    def monitor_(self) -> "_RSLDSMonitor":
        """hmmlearn-style monitor adapter exposing .history (list of ELBOs)
        and .converged (bool from the backend's plateau heuristic)."""
        return _RSLDSMonitor(history=self.elbo_history, converged=self._converged)

    @property
    def _converged(self) -> bool:
        if len(self.elbo_history) < 3:
            return False
        last3 = self.elbo_history[-3:]
        rel = abs(last3[-1] - last3[-2]) / (abs(last3[-2]) + 1e-9)
        return rel < 1e-3
```

`_RSLDSMonitor` est un petit dataclass interne avec juste `history: list[float]`
et `converged: bool`.

### 3.4 `_ElasticNetRSLDSCompat` — porté de A

Copie verbatim depuis
`Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/benchmark/models.py`
(la classe `_BenchmarkRSLDS`) qui hérite de `ElasticNetRSLDS` de Nathan
(`Projet_Robin/ssm_extensions.py`) et corrige la signature du hook
`_fit_laplace_em_params_update` pour matcher l'API du ssm pinned (commit
`eb6c8aa`).

Le shim vit dans `rslds_backend.py` (privé, préfixé `_`). Seulement instancié
quand `regularize="elastic_net"`. Si `regularize="elastic_net"` mais sklearn
manquant → `ImportError("regularize='elastic_net' requires scikit-learn, "
"included in the [rslds] extra")`.

**Décision déléguée** : ne pas modifier `Projet_Robin/ssm_extensions.py` (code
de recherche de Nathan, dans un autre repo). Le shim isolé dans
`rslds_backend.py` reste auto-suffisant.

### 3.5 Registration

Modifier `src/hmm_core/backends/__init__.py`, juste après la registration
Bayesian existante :

```python
# rSLDS backend (Phase D spike) is optional — ssm has Cython C-extensions that
# require a C compiler at install. Register lazily so users without ssm pay no
# import cost.
try:
    from hmm_core.backends.rslds_backend import RSLDSBackend

    register_backend("rslds", RSLDSBackend, default=False)
except ImportError:
    # ssm not installed — silently skip registration. get_backend("rslds") will
    # raise a clear "unknown HMM backend" error if the user tries to use it.
    RSLDSBackend = None  # type: ignore[assignment]
```

L'import paresseux du contenu lourd (`ssm`, `ssm.variational`, sklearn pour le
shim) se fait à *l'intérieur* de `RSLDSBackend.fit()` et du shim, pas au
top-level de `rslds_backend.py`, pour minimiser le coût d'import si la classe
est référencée mais jamais instanciée.

### 3.6 Dockerfile

`tools/docker/rslds.Dockerfile` = port verbatim de
`Projet_Robin/benchmark/Dockerfile` avec ajustements :
- `WORKDIR /work` au lieu de `/work/Projet_Robin`.
- Pas de hmmlearn / matplotlib / pandas dans l'image (ce sont des deps de
  hmm_studio installées séparément ; l'image rSLDS est juste l'env ssm).
  → en réalité utile aussi pour les tests, donc on les garde.
- Commentaires actualisés pointant vers hmm_studio.

Pyproject extra :
```toml
rslds = [
    # rSLDS backend (Phase D spike) — ssm has Cython C-extensions. On Windows
    # without MSVC Build Tools, use tools/docker/rslds.Dockerfile instead.
    # ssm pinned to the same commit as Projet_Robin/benchmark (A's re-benchmark).
    "ssm @ git+https://github.com/lindermanlab/ssm.git@eb6c8aa33e5311d3564075807dec340759dd8081",
    "scikit-learn>=1.3",  # for ElasticNetRSLDS regularization
    "numpy<2",            # ssm doesn't support numpy 2.x cleanly at this commit
]
```

### 3.7 Tests

**`tests/test_rslds_backend_smoke.py`** (fast tier, pas de `@slow`) — gated par
`pytest.importorskip("ssm")` au top du fichier. Trois tests :

- `test_rslds_backend_registered` — `get_backend("rslds").name == "rslds"`.
- `test_rslds_smoke_fit` — fixture `toy_X = N(0,1)` shape (60, 4). Construit une
  Topology minimale (K=3, émission gaussian, allowed_transitions = tout, fit.n_iter
  = 20). Appelle `backend.fit(topology, toy_X, seed=0, lengths=None,
  initial_transmat=uniform_3x3, initial_startprob=uniform_3, emission_kwargs={},
  mask=ones_3x3_bool)`. Assert : `isinstance(result, BackendFitResult)`,
  `result.transmat.shape == (3, 3)`, `result.startprob.shape == (3,)`,
  `np.isfinite(result.log_likelihood)`, `result.n_iter_actual == 20`,
  `hasattr(result.model, "transmat_")`, `hasattr(result.model, "dynamics_As")`,
  `result.model.D_latent == 3` (heuristique `min(K=3, n_features-1=3)`).
- `test_rslds_bundle_dual_surface` — fit comme ci-dessus, vérifie que les deux
  faces (`bundle.dynamics_As.shape == (3, D_latent, D_latent)` ET
  `bundle.transmat_.shape == (3, 3)`) sont accessibles et cohérentes
  (`transmat_` lignes somment à 1).

**`tests/test_rslds_backend.py`** (full tier, `@pytest.mark.slow`) :
- `test_rslds_plain_full_fit` — 50 iters, vérifie `score` finie, decode renvoie
  shape correcte, predict_proba shape correcte.
- `test_rslds_elasticnet_full_fit` — `regularize="elastic_net"`, vérifie que
  les dynamics A_k sont sparser que plain (vérification statistique légère).
- `test_rslds_fit_supervised_not_implemented` — `assert NotImplementedError`.
- `test_rslds_score_is_elbo_not_marginal` — appel `score`, vérifier que la
  docstring contient "NOT a marginal" ou similaire.
- `test_rslds_unknown_backend_when_extra_missing` — pas de test direct (ne peut
  pas désinstaller ssm dans le test) ; documenté manuellement.

Le test smoke n'est PAS `@slow` → s'exécute en CI normale, mais
`importorskip("ssm")` le fait skip sans installation de l'extra. Donc en CI
défaut, aucun test rslds ne tourne. Tous tournent localement avec ssm installé
ou dans le job Docker.

### 3.8 CI

`.github/workflows/rslds-docker.yml` :
```yaml
name: rSLDS backend (Docker)
on:
  workflow_dispatch:        # manuel
  schedule:
    - cron: "0 0 * * 0"     # hebdo dimanche minuit UTC

jobs:
  rslds-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build rSLDS image
        run: docker build -t hmm-studio-rslds -f tools/docker/rslds.Dockerfile .
      - name: Run rSLDS tests
        run: |
          docker run --rm -v ${{ github.workspace }}:/work -w /work \
            hmm-studio-rslds python -m pytest tests/test_rslds_backend.py \
            tests/test_rslds_backend_smoke.py -v
```

Pas dans la CI principale ; build Docker trop lourd pour chaque PR.

### 3.9 Gestion d'erreurs

| Cas | Comportement |
|---|---|
| `get_backend("rslds")` sans extra installé | `ValueError("unknown HMM backend: 'rslds' (registered: ['hmmlearn'])")` — registration skip silencieuse à l'import |
| `RSLDSBackend(regularize="elastic_net")` sans sklearn | `ImportError("regularize='elastic_net' requires scikit-learn, included in the [rslds] extra")` à l'instanciation du shim |
| `RSLDSBackend(regularize="kendall")` | `ValueError("regularize must be 'none' or 'elastic_net'...")` à `__init__` |
| `backend.fit_supervised(...)` | `NotImplementedError("rslds backend does not yet support fit_supervised (spike v0; tracked for v0.1)")` |
| Non-convergence (ELBO plateau pas atteint) | `BackendFitResult.converged=False`, pas d'exception |
| `D_latent >= n_features` (impossible avec l'heuristique mais possible si forcé) | `ValueError` levée par ssm directement ; on laisse remonter |
| `io.save_model(result)` avec model rSLDS | adapter expose `.transmat_` etc., mais le pickle de l'objet ssm peut échouer ; **caveat documenté comme limitation v0** dans la docstring + README |

### 3.10 Scope boundaries

- **Out** : exposition UI (Wizard, ComparePage, EditorCanvas). Documenté
  « drop to CLI/notebook » dans le README de l'extra.
- **Out** : intégration ComparePage. Le BIC/AIC sur ELBO n'est pas comparable
  aux mêmes métriques sur la famille HMM (précédent : NHMM, déjà
  `comparable=False` dans ComparePage).
- **Out** : `fit_supervised` pour rSLDS (raise NotImplementedError).
- **Out** : variante NHMM-style rSLDS.
- **Out** : modification du schéma topology YAML (ajout `D_latent`,
  `regularize`, `n_iter` à FitSpec). Pour le spike, valeurs hard-codées par
  heuristique + docstring caveat.
- **Out** : `io.save_model` rSLDS-aware. L'adapter expose `.transmat_` mais le
  pickle ssm peut échouer ; limitation documentée comme connue.
- **Out** : modification de `Projet_Robin/ssm_extensions.py` (code de
  recherche, dans un autre repo).
- **Out** : production-grade error messages au-delà de ImportError /
  NotImplementedError / ValueError concises.

### 3.11 Alternatives considérées

1. **Sub-package `backends/rslds/` avec submodules** (shim.py, bundle.py,
   backend.py) — rejeté : sur-ingénierie pour un spike, single-file
   `rslds_backend.py` reste lisible.
2. **No adapter, downstream code casse explicitement** — rejeté : aurait
   nécessité de patcher `io.save_model`, `_repr_html_`, NHMM dans le spike,
   gonflant le scope.
3. **Sibling protocol `ContinuousLatentBackend`** — rejeté : crée un deuxième
   chemin de dispatch et la question « quel backend répond à quoi ». À
   reconsidérer en v1 si le protocole existant force trop de compromis.
4. **Container-only (no extra Python)** — rejeté : l'extra ne coûte rien à
   déclarer et débloque les contributeurs Linux/Mac avec gcc.
5. **Production-grade backend d'emblée** — rejeté : le scope est explicitement
   spike per décision 1 ; promotion à v1 conditionnée à la validation du spike.

## 4. Promotion path : spike v0 → backend v1

Si le spike valide la faisabilité (tests verts en Docker + sanity vs A's
benchmark), promu en v1 :
1. Ajouter `D_latent`, `regularize`, `n_iter` au schéma `FitSpec` de
   `hmm_core.topology`. Documenter dans le YAML.
2. Implémenter `fit_supervised` proprement (option : raise formel avec mention
   de l'asymétrie inhérente, ou implémenter via clamping de q_train).
3. `io.save_model` rSLDS-aware : sérialiser le bundle (dynamics, emissions,
   q_train) en format custom (JSON+npz) plutôt que pickle ssm direct.
4. Suite de regression tests : faire tourner le rSLDS sur les données ETH
   d'A et asserter que les RMSE de reconstruction et le rang des modèles
   correspondent à A's benchmark_aggregated.csv.
5. Documentation utilisateur : `docs/superpowers/specs/` + section dans
   l'Academy (potentielle leçon 16 ou amendement à la leçon 15).
6. (v0.2 distincte) Page `/rslds` dédiée minimale dans le frontend, avec ses
   propres champs `D_latent`, recurrence config.

## 5. Open questions (défauts retenus, à confirmer à la relecture)

1. **Heuristique `D_latent`** : *défaut retenu* — `max(1, min(K, n_features-1))`.
   Couvre la contrainte ssm `N > D` et donne une dimension latente "raisonnable"
   pour les datasets de A (n_features=4, K∈{2,3,4,5} → D_latent ∈ {1,2,3}).
   Alternative : laisser l'utilisateur passer `D_latent` via un kwarg `fit()`
   non-standard — déconseillé pour conformer le protocole.
2. **Emplacement Dockerfile** : *défaut retenu* — `tools/docker/rslds.Dockerfile`.
   Alternative : `src/hmm_core/backends/rslds.Dockerfile`. Le choix `tools/`
   regroupe les artefacts Docker hors du source Python.
3. **Cron hebdo CI** : *défaut retenu* — ajouter le `schedule: cron 0 0 * * 0`
   pour une vérif passive. Alternative : `workflow_dispatch` seul, à lancer
   manuellement avant release.
4. **Stratégie convergence** : *défaut retenu* — plateau ELBO relatif < 1e-3
   sur les 3 derniers itérations. Alternative : trust `model.fit()`'s own
   convergence (ssm renvoie une liste d'ELBOs sans flag).

## Update 2026-06-03 — `n_iter_actual` semantic + EN test gating

Deux ajustements faits pendant l'implémentation, capturés ici pour la trace
(spec append-only).

**`BackendFitResult.n_iter_actual`.** Section 3.2 disait implicitement
`n_iter_actual = len(elbos)`. Le code livré (`rslds_backend.py:216`) renvoie
`topology.fit.n_iter` à la place. Raison : `ssm._fit_laplace_em` enregistre un
ELBO **initial** avant la première itération EM, puis ajoute un ELBO par
itération, donc `len(elbos) == num_iters + 1`. Pour respecter la sémantique
hmmlearn (« nombre d'itérations EM effectivement exécutées »), on rapporte
`num_iters`. L'historique complet (avec l'ELBO initial) reste exposé sur
`bundle.elbo_history` pour les diagnostics.

**Gating ElasticNet.** Le test `test_rslds_elasticnet_full_fit` est
explicitement skippé via `pytest.importorskip("ssm_extensions")`. Raison :
`ssm_extensions.py` vit dans le repo voisin
`Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/` et n'est ni packagé ni
copié dans l'image Docker hmm-studio-rslds. C'est cohérent avec la décision
4B/5B du spec (EN = opt-in, dépendance externe assumée) : le chemin plain
SLDS est testé bout-en-bout dans le container, le chemin EN sera testé dans
le repo crypto où `ssm_extensions` est sur le PYTHONPATH. Le shim
`_ElasticNetRSLDSCompat` lui-même est compilation-checké à l'import du
module (registration lazy dans `backends/__init__.py`).

