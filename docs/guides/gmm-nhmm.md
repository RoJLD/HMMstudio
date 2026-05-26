# GMM-NHMM: multi-modal regimes

`fit_gmm_nhmm` extends NHMM (covariate-dependent transitions) with **GMM
emissions per state**: each regime hosts a Gaussian mixture, capturing
internal sub-modes that a single Gaussian smooths out.

This is **Phase A.10**, shipped 2026-05-22. The implementation strategy
(2-stage decomposition) and its rejected alternative (`K·M` joint-state
expansion) are documented in
[ADR-0007](../decisions/0007-gmm-nhmm-scope.md) and in the
[A.10 spec](../specs/2026-05-22-phase-a10-gmm-nhmm.md).

## Quand l'utiliser

When a regime has **internal sub-modes** that you want to keep
separate without inflating the number of macro states.

Classic crypto motivation:

- A **bear** regime mixes two qualitatively different behaviours:
  *slow grinding decline* and *panic flash crash*. They share the
  same "downside risk" macro label, but their volatility and tail
  shape differ.
- A **bull** regime similarly mixes *smooth uptrend* and *FOMO
  spike*. Same regime, different micro-dynamics.

Two ways to model this with a vanilla single-Gaussian NHMM, both bad:

| Approach | Failure mode |
|---|---|
| One Gaussian per regime (K=2) | Bear/bull means are an average over sub-modes; volatility is smeared; tail behaviour is lost. |
| One regime per sub-mode (K=4) | Transitions *within* a regime (smooth-bull → FOMO-bull) get modelled as macro regime switches, polluting the transition matrix. |

**GMM-NHMM keeps K=2 macro regimes**, modulated by your covariates, and
gives each regime a `n_mix=2` Gaussian mixture. The macro transitions
mean what you want them to mean; the sub-modes live one level down.

## Comment ça marche (brièvement)

GMM-NHMM is fit via **2-stage decomposition** (Stratégie A from the
spec):

1. **Stage 1** — fit a standard GMM-HMM (`hmmlearn.GMMHMM`) on `X`
   with homogeneous transitions. This gives the mixture parameters
   $\{w_{km}, \mu_{km}, \Sigma_{km}\}$ and a Viterbi macro path.
2. **Stage 2** — for each source state $i$, fit a multinomial
   logistic regression of the *next* macro state on the covariates `Z`,
   using the Viterbi `(z_t, z_{t+1})` pairs as supervision. This yields
   the covariate-dependent transition matrix $A_{ij}(Z_t)$.

The joint EM alternative (which would treat the model as a single HMM
on $K \cdot M$ joint states with a NHMM logit over $K \cdot M$
outcomes) was **rejected** at implementation time. It looked tempting
because it would reuse the existing NHMM machinery directly, but it
over-parameterises the model: $(K \cdot M)^2 \cdot P$ free coefficients
with no constraint forcing the factorisation
$A_{ij}(Z_t) \cdot w_{jm}$ that the strict GMM-NHMM definition
requires. The 2-stage decomposition matches the math exactly with no
extra parameters. Full justification in
[ADR-0007](../decisions/0007-gmm-nhmm-scope.md).

## API

```python
def fit_gmm_nhmm(
    topology: Topology,
    X: np.ndarray,
    Z: np.ndarray,
    *,
    covariate_names: list[str],
    seed: int | None = None,
    lengths: np.ndarray | None = None,
    min_transitions: int = 10,
    regularization: float = 1.0,
) -> GMMNHMMFittedModel: ...
```

- `topology.emission.type` **must** be `"gmm"`. `n_mix` is the number
  of Gaussian components per state.
- `X` is shape `(T, n_features)`.
- `Z` is shape `(T, P)`. Each `Z[t]` drives the row-stochastic
  $A_{ij}(Z_t)$ at time $t$.
- `min_transitions` controls Stage-2 robustness: any source state with
  fewer than this many observed transitions falls back to the
  Stage-1 homogeneous transmat row (rather than fitting a degenerate
  logit on too few points).
- `regularization` is the inverse L2 strength `C` for
  `sklearn.linear_model.LogisticRegression`.

### Declare the topology

```python
from hmm_core.topology import Topology, EmissionSpec, FitSpec, InitSpec
from hmm_core.gmm_nhmm import fit_gmm_nhmm

topo = Topology(
    name="btc_regimes_with_submodes",
    n_states=2,
    state_names=["calm", "volatile"],
    emission=EmissionSpec(
        type="gmm",
        covariance_type="diag",
        n_features=2,
        n_mix=2,                       # M = 2 sub-modes per regime
    ),
    allowed_transitions=None,          # ergodic macro transitions
    startprob="uniform",
    init=InitSpec(strategy="kmeans", seed=42),
    fit=FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-4),
)
```

### Fit

```python
result = fit_gmm_nhmm(
    topo,
    X,
    Z,                                  # shape (T, P)
    covariate_names=["vol_proxy"],
    seed=42,
)
```

## Outputs

The result is a `GMMNHMMFittedModel` dataclass:

| Attribute | Shape / type | Meaning |
|---|---|---|
| `base` | `FittedModel` | Stage-1 GMM-HMM (use for `.model.means_`, `.model.weights_`, `.bic`, `.log_likelihood`). |
| `A_t` | `(T, K, K)` | Covariate-dependent transitions; row-stochastic, mask-respected. |
| `classifiers` | `dict[int, LogisticRegression]` | Stage-2 logit per source state. |
| `fallback_rows` | `dict[int, ndarray]` | Homogeneous row used when Stage-2 had too few transitions for that source. |
| `covariate_names` | `list[str]` | Echoed for traceability. |

### Convenience methods

```python
result.A_at(t)                  # K x K matrix at time t
result.n_states                 # K
result.n_mix                    # M
```

`A_at(t)` falls back to the base homogeneous transmat for `t` outside
`[0, T)`, which is occasionally useful for warm-starting downstream
analyses.

### Fallback rows

`fallback_rows` will be populated for any source state where:

- fewer than `min_transitions` `(Z_t, z_{t+1})` pairs were observed, or
- the observed next-state set has < 2 distinct values (logistic
  regression needs at least two classes).

The semantics are: that source row of $A_t$ is **time-invariant**, equal
to the homogeneous transmat row from Stage 1. Inspect
`result.fallback_rows.keys()` to see which sources fell back.

!!! tip "When fallbacks fire, you usually want either more data or fewer states"
    Frequent fallbacks usually signal a state that's barely visited.
    Either lengthen the sequence or reduce `K`.

## Diagnostics

The dataclass has a Jupyter `_repr_html_` that displays:

- A stats table (`K`, `M`, `T`, covariates, fitted classifiers count,
  log-likelihood, BIC).
- The time-averaged transition matrix heatmap.
- A per-regime sub-mode breakdown (weights and means).

Just evaluate `result` in a notebook cell.

```python
result
```

For a worked example with the 2-regime × 2-sub-mode synthetic data,
see `notebooks/05_gmm_nhmm_submodes.ipynb`.

## Model selection: GMM-NHMM vs plain NHMM

GMM-NHMM has more parameters than a single-Gaussian NHMM. BIC is the
right tool to decide whether the extra mixture components pay off:

```python
from hmm_core.nhmm import fit_nhmm

result_gmm = fit_gmm_nhmm(topo_gmm, X, Z, covariate_names=["vol_proxy"])
result_gauss = fit_nhmm(topo_gaussian, X, Z, covariate_names=["vol_proxy"])

print(f"GMM-NHMM BIC      : {result_gmm.base.bic:.1f}")
print(f"Gaussian NHMM BIC : {result_gauss.base.bic:.1f}")
```

If the data genuinely has sub-modes, GMM-NHMM should win on BIC
despite the parameter penalty. If it doesn't, that's a signal that
your regimes are already uni-modal in your features.

## Limites

These are the identifiability limits called out in the spec; the code
does **not** hard-enforce them, but going past them is asking for
trouble:

- $K \leq 4$. Beyond that the macro regimes are hard to identify even
  with rich covariates.
- $M \leq 3$. Beyond that the within-regime components become
  indistinguishable.
- $P \leq 6$ covariate columns. Each Stage-2 logit has $K \cdot P$
  free coefficients per source; running thin on transitions makes them
  unstable.
- $T \gtrsim 200 \cdot \text{free\_params}$ rule of thumb for
  stability.

Label switching (state permutation across re-fits) is **not** handled
inside `fit_gmm_nhmm` itself. If you re-fit with a different seed and
get permuted state labels, post-process by sorting states on (e.g.)
$\mu_{k,1}$.

## Voir aussi

- [Phase A.10 spec](../specs/2026-05-22-phase-a10-gmm-nhmm.md) — full
  math derivation, EM equations, history of the rejected Strategy A.
- [ADR-0007](../decisions/0007-gmm-nhmm-scope.md) — why 2-stage, why
  no joint EM in MVP.
- [Factorial NHMM guide](factorial-nhmm.md) — the same 2-stage pattern
  applied to independent regime *dimensions* instead of internal
  sub-modes.
- `notebooks/05_gmm_nhmm_submodes.ipynb` — runnable end-to-end with
  synthetic 2×2 data.
