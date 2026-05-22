# hmm-studio

HMM topology editor, constrained fit engine, and visualizer.

This repo currently ships **`hmm-core`** — a domain-agnostic Python engine
for fitting HMMs with structurally constrained transition matrices.
A future `hmm-studio` web UI (node-based topology editor) will sit on top
of `hmm-core` and is tracked in the [roadmap](roadmap.md).

## Why this exists

`hmmlearn` (and most HMM libraries) fit ergodic models: every transition
edge is free. Real applications often need **structural priors** — Bakis
left-right speech models, lifecycle models with forbidden back-transitions,
branching topologies. `hmm-core` lets you declare which transitions are
allowed and runs constrained Baum-Welch that respects those zeros at every
M-step.

[Get started →](getting-started.md){ .md-button .md-button--primary }
[See the roadmap →](roadmap.md){ .md-button }

## Project status (2026-05-22)

| Sub-project | Status | Notes |
|---|---|---|
| **A — hmm-core** | ✅ v0.2.0 shipped | 66 tests, 92% coverage, NHMM included |
| **D — crypto dashboard migration** | ✅ Swapped | Internal swap done; regression test passes |
| **Z.1 — CI** | ✅ Configured | GitHub Actions ready; awaiting remote |
| **B — web UI** | 📐 Spec drafted | 6 open decisions to arbitrate before implementation |
| **C — advanced viz** | 📐 Spec drafted | Depends on B |
| **Z.3 — v1.0 release** | ⏳ Pending | After B + C ship |
