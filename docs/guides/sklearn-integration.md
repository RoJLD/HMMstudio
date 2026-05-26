# Drop-in with scikit-learn

`HMMClassifier` is hmm-studio's scikit-learn-compatible wrapper around
`hmm_core.fit`. It is a real `BaseEstimator` + `ClassifierMixin`, passes
`sklearn.utils.estimator_checks.check_estimator`, and slots into any
sklearn workflow — `Pipeline`, `GridSearchCV`, `cross_val_score`,
`sklearn.base.clone`, `joblib.dump` — without ceremony.

This is **Phase I.2** of the hybrid distribution strategy
([ADR-0012](../decisions/0012-distribution-strategy-hybrid.md)). The HMM
math stays in `hmm_core`; the wrapper is a thin contract layer.

## 30-second pitch

```python
from hmm_core.sklearn_compat import HMMClassifier

clf = HMMClassifier(n_states=3, emission_type="gaussian", n_features=2)
clf.fit(X)
clf.predict(X)
clf.score(X)            # log-likelihood per timestep
```

That's it. Every sklearn idiom you already know — `get_params`,
`set_params`, `clone`, `Pipeline.steps`, `GridSearchCV.best_estimator_`
— works on it.

## Quick example: 2-state Gaussian

```python
import numpy as np
from hmm_core.sklearn_compat import HMMClassifier

rng = np.random.default_rng(42)
X = np.concatenate([
    rng.normal(0.0, 0.5, (80, 1)),
    rng.normal(5.0, 0.5, (80, 1)),
    rng.normal(0.0, 0.5, (80, 1)),
    rng.normal(5.0, 0.5, (80, 1)),
])

clf = HMMClassifier(n_states=2, n_iter=50).fit(X)
print(clf.predict(X)[:10])
print(f"BIC = {clf.bic_:.2f}, converged = {clf.converged_}")
```

Fitted attributes follow the sklearn `*_` convention :

| Attribute | Meaning |
|---|---|
| `transmat_` | `(K, K)` fitted transition matrix |
| `startprob_` | `(K,)` initial distribution |
| `classes_` | integer labels `[0, ..., n_states - 1]` |
| `n_iter_` | number of EM iterations actually run |
| `log_likelihood_`, `bic_`, `aic_` | information criteria |
| `converged_` | bool |
| `n_features_in_` | sklearn standard |

## Pipelines

Standard sklearn preprocessing in front of the HMM:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from hmm_core.sklearn_compat import HMMClassifier

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("hmm", HMMClassifier(n_states=3, n_iter=50)),
])
pipe.fit(X)
pipe.named_steps["hmm"].bic_
```

`Pipeline` calls `fit` then `transform` on every step except the last,
exactly as for any sklearn estimator. `StandardScaler` is a common
front-end since EM convergence on Gaussian emissions is sensitive to
input scale.

## Grid search over hyperparameters

`HMMClassifier.__init__` exposes only simple parameters (no `Topology`
object), which is what sklearn needs for `get_params` / `set_params`.
That means `GridSearchCV` works out of the box on the natural HMM
hyperparameters:

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    "n_states": [2, 3, 4],
    "init_strategy": ["kmeans", "random"],
    "emission_type": ["gaussian"],
}
search = GridSearchCV(
    HMMClassifier(n_iter=30),
    param_grid,
    cv=3,
    scoring="accuracy",   # if y is provided ; else use a custom scorer
    n_jobs=1,
)
search.fit(X, y_true)
print(search.best_params_)
print(search.best_estimator_.bic_)
```

!!! warning "Random splits are wrong for time series"
    HMMs assume sequential data. `cv=KFold` shuffles, which destroys
    the temporal structure. Use `TimeSeriesSplit` for any non-toy
    dataset — see below.

## Cross-validation with `TimeSeriesSplit`

```python
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from hmm_core.sklearn_compat import HMMClassifier

scores = cross_val_score(
    HMMClassifier(n_states=2, n_iter=30),
    X, y_true,
    cv=TimeSeriesSplit(n_splits=5),
    scoring="accuracy",
)
print(f"{scores.mean():.3f} ± {scores.std():.3f}")
```

### Custom scorer (unsupervised, log-likelihood-based)

The default `score(X)` returns log-likelihood per timestep. Wrap it as a
sklearn scorer if you want unsupervised CV:

```python
from sklearn.metrics import make_scorer

def loglik_per_step(estimator, X, y=None):
    return estimator.score(X)   # already log-lik per t when y is None

scores = cross_val_score(
    HMMClassifier(n_states=3),
    X,
    cv=TimeSeriesSplit(n_splits=5),
    scoring=loglik_per_step,
)
```

## `clone()` and `joblib` round-trip

`sklearn.base.clone` produces a fresh, unfitted estimator with the same
constructor params — useful for parallel grid searches:

```python
from sklearn.base import clone

clf = HMMClassifier(n_states=4, init_seed=7)
clf2 = clone(clf)
clf2.get_params() == clf.get_params()   # True
```

`joblib` persistence is the sklearn-standard route. `HMMClassifier`
holds the fitted `result_` attribute, which is a plain dataclass
containing the underlying hmmlearn model — both pickle cleanly:

```python
import joblib

clf.fit(X)
joblib.dump(clf, "btc_hmm.joblib")

loaded = joblib.load("btc_hmm.joblib")
np.allclose(loaded.predict(X), clf.predict(X))   # True
```

## Supervised mode

When you have state labels, `fit(X, y)` switches to closed-form MLE
(no EM iterations). That's also why `HMMClassifier` is registered as a
`ClassifierMixin` — it implements `score(X, y) = accuracy`:

```python
clf = HMMClassifier(n_states=2).fit(X, y_true)
print(clf.n_iter_)              # 1 — supervised is one-pass
print(clf.score(X_test, y_test)) # accuracy
```

## What `HMMClassifier` does NOT do

- **It is not a generic supervised classifier.** The HMM models the
  *unsupervised regime structure* of the observation sequence. Passing
  `y` makes it supervised in the closed-form sense (you provide the
  states), but the model is still about temporal dynamics, not iid
  feature → label mapping.
- **It does not expose NHMM, GMM-NHMM, or Factorial NHMM.** Those have
  richer signatures (per-chain covariates, mixture components per state)
  that don't fit the simple-parameters constraint of sklearn's
  `__init__`. Use `hmm_core.nhmm.fit_nhmm`,
  `hmm_core.gmm_nhmm.fit_gmm_nhmm`, and
  `hmm_core.factorial_nhmm.fit_factorial_nhmm` directly. An sklearn
  wrapper for NHMM is on the roadmap as Phase I.2.1.
- **It does not handle multi-sequence input.** Pass one long sequence
  per fit; concatenate manually if needed.

## Constructor parameters

Full signature, all defaults:

```python
HMMClassifier(
    n_states=3,
    emission_type="gaussian",     # "gaussian" | "gmm" | "multinomial" | "poisson"
    covariance_type="diag",       # gaussian/gmm only
    n_features=1,
    n_mix=None,                   # required if emission_type="gmm"
    n_symbols=None,               # required if emission_type="multinomial"
    allowed_transitions=None,     # list of (src, dst) state-name pairs, or None for ergodic
    startprob="uniform",          # "uniform" | "first_state" | list[float]
    init_strategy="kmeans",       # "uniform" | "random" | "kmeans" | "data_frequencies"
    init_seed=42,
    n_iter=100,
    tol=1e-4,
)
```

State names follow the convention `["s0", "s1", ..., "s{n_states-1}"]`,
which is what `allowed_transitions` references.

## Voir aussi

- `notebooks/04_sklearn_pipeline.ipynb` — runnable end-to-end example
  (pipeline, grid search, time-series CV, joblib).
- [ADR-0012](../decisions/0012-distribution-strategy-hybrid.md) — why
  hmm-studio ships an sklearn surface instead of a wholly bespoke API.
