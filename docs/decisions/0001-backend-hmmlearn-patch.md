# ADR-0001: HMM backend choice — patched `hmmlearn` vs `pomegranate`

**Date**: 2026-05-21
**Status**: Accepted

## Context

`hmm-core` needs to fit HMMs with structural constraints on the transition
matrix (forbidden edges forced to 0 throughout Baum-Welch). The two
realistic Python backends are:

1. **`hmmlearn`** — mature, scipy-style API, used by the existing crypto
   dashboard in `Experiment.Crypto.2026S1.RobinDenis`. Does NOT support
   transition constraints natively.
2. **`pomegranate`** — younger, PyTorch backend, supports structured
   topologies natively (`edge_inertia`, masked transitions).

## Decision

Subclass `hmmlearn` emission classes (`GaussianHMM`, `GMMHMM`,
`CategoricalHMM`, `PoissonHMM`) and override `_do_mstep` to apply a binary
mask + row-renormalize after each M-step.

## Alternatives considered

- **Switch to `pomegranate`** — rejected: rupture with the dashboard that
  already consumes `hmmlearn`, and v1.x is still consolidating with
  incomplete documentation as of 2026-05.
- **Hybrid backend** (`hmmlearn` ergodic, `pomegranate` constrained) —
  rejected: maintaining two API shapes (state ordering, posterior layout)
  is over-engineering for the same problem.

## Consequences

**Positive**
- ~30 lines of subclass code per emission, no copy-paste of Baum-Welch.
- Drop-in compatible with the existing dashboard.
- Tests are simple: vanilla equivalence when `mask=None`, mask preserved
  after fit.

**Negative**
- `_do_mstep` is a semi-private API; an `hmmlearn` minor-version bump
  could change its signature. Mitigation: pin `hmmlearn>=0.3,<0.4`,
  re-test before bumping the upper bound.
- Subtly different `_do_mstep` signatures across emission classes mean
  each subclass needs its own dedicated test (see
  `tests/test_constraints_<emission>.py`).

## Revisit triggers

- `hmmlearn>=0.4` lands and changes `_do_mstep`.
- A use case requires emission-level constraints (tied means, edge-tied
  transitions) that the mask-only approach cannot express.
