# Factorial NHMM: multi-factor regimes

`fit_factorial_nhmm` models a process driven by **D independent regime
chains** evolving in parallel, each with its own state set, its own
covariates, and its own transition matrix. The chains share a joint
emission over `X` but their dynamics are decoupled.

This is **Phase A.13**, shipped 2026-05-22. The implementation strategy
(2-stage decomposition over the joint product space, with a hard cap
$K_{joint} = \prod_d K_d \leq 27$) is documented in the
[A.13 spec](../specs/2026-05-22-phase-a13-factorial-nhmm.md).

## Quand l'utiliser

When the market — or whatever you're modelling — has **multiple
independent regime dimensions** that don't reduce to one. Canonical
crypto example:

- **Trend** ∈ {down, flat, up} — directional orientation
- **Volatility** ∈ {low-vol, normal, high-vol} — agitation level
- **Macro** ∈ {risk-on, risk-off} — cross-asset context

A flat 18-state HMM ($3 \times 3 \times 2$) over the joint regime
would force **synchronous transitions**: all three dimensions change
together or none of them do. Empirically wrong:

- Vol can spike (low → high) without the trend changing direction.
- Macro can flip (risk-on → risk-off) before trend reacts.
- Each dimension has its own time constant.

A Factorial NHMM keeps the three chains separate. Each chain has its
own transition matrix and its own covariates. The chains decode
independently.

## Comment ça marche (brièvement)

Stratégie A — **2-stage decomposition**, the same pattern as
[GMM-NHMM](gmm-nhmm.md):

1. **Stage 1** — fit a standard Gaussian HMM on the **joint product
   space** $K_{joint} = \prod_d K_d$ states with ergodic transitions.
   This gives the joint emission parameters $\mu_{(k_1, \dots, k_D)},
   \Sigma_{(k_1, \dots, k_D)}$ and a joint Viterbi
   $\hat z_t \in [0, K_{joint})$.
2. **Stage 2** — project the joint Viterbi to per-chain trajectories
   via `np.unravel_index`. For each chain $d$ and each source state
   $i \in [K_d]$, fit a multinomial logistic regression of the next
   chain state on chain $d$'s own covariates $u^{(d)}_t$.

The joint-logit alternative (which would treat all of
$\prod_d K_d$ outcomes as targets of a single huge logit per joint
source state) was **rejected** at implementation time for the same
reason as GMM-NHMM's K·M expansion: it over-parameterises. A
joint-logit would have $(\prod_d K_d)^2 \cdot P$ free coefficients
with no constraint enforcing the factorisation
$\prod_d A^{(d)}_{i_d j_d}(u^{(d)}_t)$ that the strict Factorial
definition requires. The 2-stage decomposition matches the math with
no extras. See the
[A.13 spec § 3](../specs/2026-05-22-phase-a13-factorial-nhmm.md) for
the full argument.

## Parameter savings

The whole point of going factorial is the parameter count of the
transition machinery. For $D$ chains of $K_d$ states each, evaluated
on $P$ covariates per chain:

- **Joint NHMM** : $(\prod_d K_d)^2 \cdot P$ free transition logit
  coefficients.
- **Factorial NHMM** : $\sum_d K_d^2 \cdot P$ free coefficients.

Concrete case: $D=3$ chains, $K_d=3$ each, $P=1$ covariate per chain.

| Model | Free transition coefficients |
|---|---|
| Joint NHMM on $K_{joint} = 27$ states | $27^2 = 729$ |
| Factorial NHMM, 3 chains of 3 states | $3 \cdot 3^2 = 27$ |

**27× fewer free coefficients**, which translates directly to better
identifiability on short series.

```python
K_per_chain = result.K_per_chain        # [3, 3, 3]
K_joint = result.K_joint                # 27
joint_params = K_joint ** 2             # 729
factorial_params = sum(k ** 2 for k in K_per_chain)  # 27
print(f"savings: {joint_params / factorial_params:.1f}x")  # 27.0x
```

## API

```python
def fit_factorial_nhmm(
    chains: list[FactorialChainSpec],
    X: np.ndarray,
    covariates_per_chain: dict[str, np.ndarray],
    *,
    emission: EmissionSpec,
    covariate_names_per_chain: dict[str, list[str]] | None = None,
    fit_spec: FitSpec | None = None,
    init: InitSpec | None = None,
    startprob: str | list[float] = "uniform",
    seed: int | None = None,
    lengths: np.ndarray | None = None,
    min_transitions: int = 10,
    regularization: float = 1.0,
) -> FactorialNHMMFittedModel: ...
```

- `chains` is a list of `FactorialChainSpec(name, n_states)`. **Order
  matters** — it determines the joint state indexing via
  `np.unravel_index` in row-major order.
- `X` is shape `(T, n_features)`. Must match `emission.n_features`.
- `covariates_per_chain` is a dict `{chain_name: ndarray(T, P_d)}`.
  Each chain has **its own** covariates; they can overlap or be
  entirely distinct.
- `emission` is the joint emission spec. MVP supports only
  `type="gaussian"`; GMM / multinomial / poisson joint emissions are
  deferred.
- `min_transitions` and `regularization` follow the same semantics as
  in [GMM-NHMM](gmm-nhmm.md).

### Declare chains and fit

```python
from hmm_core.factorial_nhmm import FactorialChainSpec, fit_factorial_nhmm
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec

chains = [
    FactorialChainSpec(name="trend",      n_states=3),
    FactorialChainSpec(name="vol",        n_states=2),
]

result = fit_factorial_nhmm(
    chains,
    X,                                  # shape (T, 2)
    covariates_per_chain={
        "trend": macro_index,           # (T, 1)
        "vol":   fear_index,            # (T, 1)
    },
    covariate_names_per_chain={
        "trend": ["macro_index"],
        "vol":   ["fear_index"],
    },
    emission=EmissionSpec(type="gaussian", covariance_type="diag", n_features=2),
    fit_spec=FitSpec(algorithm="baum_welch", n_iter=50, tol=1e-3),
    init=InitSpec(strategy="kmeans", seed=42),
    seed=42,
)
```

## Outputs

The result is a `FactorialNHMMFittedModel` dataclass:

| Attribute | Type | Meaning |
|---|---|---|
| `base` | `FittedModel` | Stage-1 joint Gaussian HMM (use for joint emission, joint log-likelihood, joint BIC). |
| `chain_specs` | `list[FactorialChainSpec]` | Echoed, in declared order. |
| `chain_classifiers` | `dict[str, dict[int, LogisticRegression]]` | Per-chain, per-source-state Stage-2 logits. |
| `chain_fallback_rows` | `dict[str, dict[int, ndarray]]` | Per-chain fallback rows (empirical row from the chain's Viterbi). |
| `A_t_per_chain` | `dict[str, ndarray(T, K_d, K_d)]` | Per-chain covariate-dependent transitions. |
| `chain_covariate_names` | `dict[str, list[str]]` | Echoed for traceability. |

### Derived properties

```python
result.chain_names         # ["trend", "vol"]
result.K_per_chain         # [3, 2]
result.K_joint             # 6
result.n_chains            # 2
```

### Decoding

Two granularities:

```python
# Joint Viterbi over the product space
joint_path = result.decode_joint(X)               # (T,) in [0, K_joint)

# Per-chain Viterbi, projected via np.unravel_index
trend_path = result.decode_chain(X, "trend")      # (T,) in [0, 3)
vol_path = result.decode_chain(X, "vol")          # (T,) in [0, 2)
```

The per-chain decode is **not** a separate inference — it's the same
joint Viterbi unravelled along each chain's axis.

### Time-varying transitions

```python
A_trend = result.A_t("trend")          # (T, 3, 3), row-stochastic
A_vol = result.A_t("vol")              # (T, 2, 2)

print(A_trend.mean(axis=0).round(3))   # average transition matrix
```

Each chain's $A_t$ is driven **only** by that chain's covariates. There
is no cross-chain coupling in the transition machinery — the chains
are explicitly Markov-independent given their respective covariates.

## Diagnostics

The Jupyter `_repr_html_` renders:

- A stats table (`D`, `K_per_chain`, `K_joint`, `T`, chain names,
  joint log-likelihood, joint BIC).
- A per-chain heatmap of the time-averaged transition matrix.

```python
result
```

A runnable end-to-end with a 3-state trend chain × 2-state vol chain
is in `notebooks/06_factorial_nhmm_multifactor.ipynb`.

## Limites

The MVP enforces three hard limits at fit time:

| Limit | Enforcement | Why |
|---|---|---|
| `K_joint = ∏K_d ≤ 27` | `raise TopologyError` | Joint product space explodes; Strategy B (variational) is required beyond this, and it is deferred until a real use case demands it. |
| `emission.type == "gaussian"` | `raise TopologyError` | Joint GMM / multinomial / poisson emissions deferred to A.13.x. |
| Chain names unique | `raise ValueError` | Used as dict keys throughout. |

Soft limits, called out but not enforced:

- $D \leq 3$ chains. Beyond that the joint product space exceeds 27
  even with $K_d = 2$.
- $K_d \leq 3$ per chain. Same reason.
- $P_d \leq 6$ covariates per chain. Each Stage-2 logit is
  $K_d \cdot P_d$ free coefficients per source.
- $T \gtrsim 300 \cdot \text{free\_params}$ as a rule of thumb.

Label switching is **per chain**. Within a chain, post-process by
sorting states on (e.g.) the joint emission means projected onto that
chain's axis. Across chains, the names you provided (`trend`, `vol`,
`macro`) are the identity — there is no permutation invariance.

## Fallback rows

For each chain, any source state with fewer than `min_transitions`
observed in the projected Viterbi falls back to the **empirical
homogeneous row** for that chain (smoothed with a tiny uniform
pseudocount). Inspect `result.chain_fallback_rows[chain_name]` to see
which sources fell back.

This is the same pattern as [GMM-NHMM](gmm-nhmm.md) — the per-chain
projected Viterbi can have very few transitions out of rarely-visited
chain states, and a degenerate logit on a handful of points would be
worse than the homogeneous fallback.

## Voir aussi

- [Phase A.13 spec](../specs/2026-05-22-phase-a13-factorial-nhmm.md)
  — full derivation, Ghahramani–Jordan references, history of the
  rejected joint-logit Strategy A.
- [GMM-NHMM guide](gmm-nhmm.md) — same 2-stage decomposition pattern,
  applied to within-regime sub-modes instead of across-regime
  dimensions.
- `notebooks/06_factorial_nhmm_multifactor.ipynb` — runnable
  end-to-end with synthetic trend × vol data.
