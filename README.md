# hmm-studio

HMM topology editor, constrained fit engine, and visualizer.

This repo currently ships the **`hmm-core`** sub-package: a domain-agnostic
Python engine for fitting HMMs with structurally constrained transition
matrices.

## Install (dev)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Quick test

```bash
pytest -v
```

Full documentation: `docs/specs/2026-05-21-hmm-core-design.md`.
