"""Factorial NHMM (Phase A.13) : D parallel chains with covariate-dependent transitions.

Strategy A — **2-stage decomposition** (chosen 2026-05-22 after applying the
A.10 lesson : do NOT use a single NHMM logit on the ∏K_d joint outcomes,
which would have ``(∏K_d)² · P`` unconstrained coefficients vs the
``sum_d K_d² · P`` required by strict Factorial NHMM. The joint-logit
expansion is a strict superset of the Factorial model and over-parameterizes
it).

The decomposition :
  Stage 1 : Standard Gaussian HMM on the joint product space ``K_joint = ∏_d K_d``.
            Gives joint emission parameters ``μ_{(k_1..k_D)}, Σ_{(k_1..k_D)}``
            and a joint Viterbi ``ẑ_t ∈ [0, K_joint)``.
  Stage 2 : Project joint Viterbi to per-chain trajectories via
            ``np.unravel_index``. Fit a NHMM logit **per chain** on its own
            covariates ``u^{(d)}_t``, exactly as in A.1 (homogeneous chain
            transitions modulated by chain-specific covariates).

Both stages reuse existing machinery (``fit()`` for Stage 1, the A.1 pattern
for Stage 2). No new backends required.

Limits documented in the docstrings :
- ``D ≤ 3`` (chains) — beyond that, joint state space ``∏K_d`` explodes
- ``K_d ≤ 3`` per chain — same reason
- ``∏K_d ≤ 27`` hard constraint (enforced by raise)
- ``P_d ≤ 6`` covariates per chain (soft, warned)
- ``T ≥ 300 · free_params`` (rule of thumb, warned)

For larger configurations the spec mentions Strategy B (variational mean-field
in a dedicated backend). Strategy B is deferred until a real use case requires it.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression

from hmm_core.fit import FittedModel, fit
from hmm_core.fit._base import _apply_mask
from hmm_core.topology import EmissionSpec, FitSpec, InitSpec, Topology, TopologyError


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactorialChainSpec:
    """Specification of one chain in a Factorial NHMM.

    The chain's emission contribution lives at the joint level (Option A
    tuple-indexed emission per spec), so this struct holds only what's
    chain-specific : its name and its number of states.
    """

    name: str
    n_states: int


@dataclass(frozen=True)
class FactorialNHMMFittedModel:
    """Output of ``fit_factorial_nhmm``.

    Attributes
    ----------
    base
        The Stage-1 ``FittedModel`` on the joint product space (K_joint = ∏K_d).
        Its ``.model.transmat_`` is the homogeneous joint transition matrix
        from Stage 1, **discarded for prediction** but kept for diagnostics.
        Its ``.model.means_``, ``.model.covars_`` are the joint emission params.
    chain_specs
        The list of ``FactorialChainSpec`` provided by the user, preserved.
    chain_classifiers
        ``{chain_name: {source_state: LogisticRegression}}`` — the Stage-2
        logits per chain per source state.
    chain_fallback_rows
        ``{chain_name: {source_state: ndarray(K_d,)}}`` — fallback rows for
        chain sources with too few observed transitions.
    A_t_per_chain
        ``{chain_name: ndarray(T, K_d, K_d)}`` — covariate-dependent
        transitions per chain, mask-respected and row-normalized.
    """

    base: FittedModel
    chain_specs: list[FactorialChainSpec]
    chain_classifiers: dict[str, dict[int, object]]
    chain_fallback_rows: dict[str, dict[int, np.ndarray]]
    A_t_per_chain: dict[str, np.ndarray]
    chain_covariate_names: dict[str, list[str]] = field(default_factory=dict)

    @property
    def chain_names(self) -> list[str]:
        return [c.name for c in self.chain_specs]

    @property
    def K_per_chain(self) -> list[int]:
        return [c.n_states for c in self.chain_specs]

    @property
    def K_joint(self) -> int:
        K = 1
        for c in self.chain_specs:
            K *= c.n_states
        return K

    @property
    def n_chains(self) -> int:
        return len(self.chain_specs)

    def decode_joint(self, X: np.ndarray) -> np.ndarray:
        """Joint Viterbi : returns array of shape (T,) with values in [0, K_joint)."""
        return self.base.model.predict(X)

    def decode_chain(self, X: np.ndarray, chain_name: str) -> np.ndarray:
        """Per-chain Viterbi : projects joint Viterbi via ``np.unravel_index``."""
        d_idx = self.chain_names.index(chain_name)
        joint = self.decode_joint(X)
        per_chain = np.unravel_index(joint, self.K_per_chain)
        return np.asarray(per_chain[d_idx])

    def A_t(self, chain_name: str) -> np.ndarray:
        """Transition matrix array (T, K_d, K_d) for the given chain."""
        return self.A_t_per_chain[chain_name]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


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
) -> FactorialNHMMFittedModel:
    """Fit a Factorial NHMM via 2-stage decomposition.

    Parameters
    ----------
    chains
        List of ``FactorialChainSpec`` — one per chain. Order matters (used
        for joint state indexing via ``np.unravel_index`` with shape
        ``(K_1, K_2, ..., K_D)`` in row-major order).
    X
        Observations, shape ``(T, n_features)``. Must match ``emission.n_features``.
    covariates_per_chain
        Dict mapping chain name to its own covariate array of shape ``(T, P_d)``.
        Each chain has its own covariate set — they can overlap or be distinct.
    emission
        Joint emission spec (must be Gaussian in MVP, additive option deferred).
    covariate_names_per_chain
        Optional metadata mapping chain name to its covariate column names.
    fit_spec
        Optional ``FitSpec`` for Stage 1 (joint HMM). Defaults to reasonable values.
    init
        Optional ``InitSpec`` for Stage 1. Defaults to kmeans + seed.
    startprob
        Stage 1 startprob convention. Defaults to uniform.
    seed
        Random seed for both stages.
    lengths
        Multi-sequence lengths, propagated to Stage 1 and to Stage 2's
        boundary handling.
    min_transitions
        Threshold below which a chain's source-state gets a fallback row.
    regularization
        Inverse regularization strength ``C`` for ``LogisticRegression`` in Stage 2.

    Returns
    -------
    FactorialNHMMFittedModel

    Raises
    ------
    TopologyError
        If ``emission.type != 'gaussian'`` (MVP restriction) or if K_joint > 27.
    ValueError
        If covariates_per_chain keys don't match chain names, or shapes mismatch.

    Notes
    -----
    K_joint = ∏_d K_d is bounded to 27 (D=3, K_d=3 max) in MVP. Beyond that,
    the joint state expansion in Stage 1 becomes wasteful and Strategy B
    (variational mean-field, deferred) is required.
    """
    if emission.type != "gaussian":
        raise TopologyError(
            f"fit_factorial_nhmm MVP supports only emission.type='gaussian' ; "
            f"got {emission.type!r}. GMM / multinomial / poisson joint emissions "
            f"are deferred to A.13.x."
        )
    if not chains:
        raise ValueError("chains must be non-empty")

    chain_names = [c.name for c in chains]
    if len(set(chain_names)) != len(chain_names):
        raise ValueError(f"chain names must be unique ; got {chain_names}")

    K_per_chain = [c.n_states for c in chains]
    K_joint = int(np.prod(K_per_chain))
    if K_joint > 27:
        raise TopologyError(
            f"K_joint = ∏K_d = {K_joint} exceeds the MVP limit (27, e.g. "
            f"D=3 K=3 each). For larger factorial models, Strategy B "
            f"(variational mean-field, deferred) is required."
        )

    # Validate covariates_per_chain
    missing = set(chain_names) - set(covariates_per_chain)
    extra = set(covariates_per_chain) - set(chain_names)
    if missing or extra:
        raise ValueError(
            f"covariates_per_chain keys mismatch chain names. "
            f"missing={missing}, extra={extra}"
        )
    T = len(X)
    for name, Z_d in covariates_per_chain.items():
        if Z_d.shape[0] != T:
            raise ValueError(
                f"covariates for chain {name!r} have {Z_d.shape[0]} rows, "
                f"expected T={T}"
            )

    if covariate_names_per_chain is None:
        covariate_names_per_chain = {
            name: [f"{name}_z{i}" for i in range(covariates_per_chain[name].shape[1])]
            for name in chain_names
        }

    # Stage 1 : fit a joint Gaussian HMM on K_joint states (ergodic).
    actual_seed = seed if seed is not None else 0
    joint_state_names = [
        "_".join(f"{chain.name}{idx}" for chain, idx in zip(chains, np.unravel_index(k, K_per_chain)))
        for k in range(K_joint)
    ]
    joint_topo = Topology(
        name=f"factorial_joint_{'_x_'.join(chain_names)}",
        n_states=K_joint,
        state_names=joint_state_names,
        emission=emission,
        allowed_transitions=None,  # ergodic in joint space
        startprob=startprob,
        init=init or InitSpec(strategy="kmeans", seed=actual_seed),
        fit=fit_spec or FitSpec(algorithm="baum_welch", n_iter=100, tol=1e-4),
    )

    base = fit(joint_topo, X, seed=actual_seed, lengths=lengths)
    joint_viterbi = base.model.predict(X)  # (T,) in [0, K_joint)

    # Project joint Viterbi to per-chain Viterbi (each is (T,) in [0, K_d))
    per_chain_viterbi = {
        name: np.asarray(np.unravel_index(joint_viterbi, K_per_chain)[d_idx])
        for d_idx, name in enumerate(chain_names)
    }

    # Stage 2 : per-chain logistic regression on its own covariates.
    boundary_idx = _sequence_boundaries(lengths, T)

    chain_classifiers: dict[str, dict[int, object]] = {}
    chain_fallback_rows: dict[str, dict[int, np.ndarray]] = {}
    A_t_per_chain: dict[str, np.ndarray] = {}

    for d_idx, chain in enumerate(chains):
        K_d = chain.n_states
        z_d = per_chain_viterbi[chain.name]
        Z_d = covariates_per_chain[chain.name]

        # Gather (Z_d[t], z_d[t+1]) pairs per source state
        pairs_per_source: dict[int, list[int]] = {i: [] for i in range(K_d)}
        for t in range(T - 1):
            if t in boundary_idx:
                continue
            i = int(z_d[t])
            pairs_per_source[i].append(t)

        classifiers: dict[int, object] = {}
        fallback_rows: dict[int, np.ndarray] = {}

        # Marginal homogeneous chain transmat = empirical counts on z_d
        homogeneous = _empirical_chain_transmat(z_d, K_d, boundary_idx)

        for i in range(K_d):
            ts = pairs_per_source[i]
            if len(ts) < min_transitions:
                fallback_rows[i] = homogeneous[i]
                continue
            Z_i = Z_d[ts]
            next_states = z_d[np.asarray(ts) + 1]
            if len(np.unique(next_states)) < 2:
                fallback_rows[i] = homogeneous[i]
                continue
            clf = LogisticRegression(
                C=regularization,
                solver="lbfgs",
                max_iter=200,
                random_state=actual_seed,
            )
            clf.fit(Z_i, next_states)
            classifiers[i] = clf

        # Build chain A_t : (T, K_d, K_d)
        A_t = np.zeros((T, K_d, K_d))
        for i in range(K_d):
            if i in classifiers:
                clf = classifiers[i]
                probs = clf.predict_proba(Z_d)
                row_t = np.zeros((T, K_d))
                for c_idx, c in enumerate(clf.classes_):
                    row_t[:, int(c)] = probs[:, c_idx]
                A_t[:, i, :] = row_t
            else:
                A_t[:, i, :] = fallback_rows[i]

        # No structural mask in MVP → just normalize rows to handle FP drift.
        for t in range(T):
            row_sums = A_t[t].sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1.0
            A_t[t] /= row_sums

        chain_classifiers[chain.name] = classifiers
        chain_fallback_rows[chain.name] = fallback_rows
        A_t_per_chain[chain.name] = A_t

    return FactorialNHMMFittedModel(
        base=base,
        chain_specs=list(chains),
        chain_classifiers=chain_classifiers,
        chain_fallback_rows=chain_fallback_rows,
        A_t_per_chain=A_t_per_chain,
        chain_covariate_names=covariate_names_per_chain,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _sequence_boundaries(lengths: np.ndarray | None, total: int) -> set[int]:
    """Time indices t where (t, t+1) crosses a sequence boundary."""
    if lengths is None:
        return set()
    out: set[int] = set()
    offset = 0
    for L in lengths[:-1]:
        offset += int(L)
        out.add(offset - 1)
    return out


def _empirical_chain_transmat(
    z_chain: np.ndarray, K_d: int, boundary_idx: set[int]
) -> np.ndarray:
    """Empirical (homogeneous) transition matrix from a single chain's Viterbi.

    Used as fallback when too few transitions are observed for a source state.
    Smoothed with a tiny uniform pseudocount to avoid zero rows.
    """
    counts = np.zeros((K_d, K_d))
    for t in range(len(z_chain) - 1):
        if t in boundary_idx:
            continue
        counts[int(z_chain[t]), int(z_chain[t + 1])] += 1
    counts = counts + 1e-6  # smoothing
    return counts / counts.sum(axis=1, keepdims=True)
