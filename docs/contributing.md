# Contributing

Thanks for considering a contribution to `hmm-studio`. This is a small but
ambitious project — the more eyes, the better.

## Getting set up

```bash
git clone https://github.com/<user>/hmm-studio.git
cd hmm-studio

# Python side
python -m venv .venv
.venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e ".[web,dev,docs]"

# Frontend side
cd src/hmm_studio/frontend
npm install
npm run build
cd ../../..

# Run the tests
pytest -q
pytest validation/ -m validation     # scientific validation suite (slower)

# Run the docs locally
mkdocs serve   # http://127.0.0.1:8000

# Run the studio
hmm-studio     # http://127.0.0.1:8000
```

## Project structure

| Path | Purpose |
|---|---|
| `src/hmm_core/` | Python engine: constrained fit, NHMM, GMM, supervised, Dirichlet priors |
| `src/hmm_studio/` | Web UI: FastAPI backend + React frontend |
| `tests/` | Code-correctness tests (pytest, fast) |
| `validation/` | Scientific validation tests (cross-check vs hmmlearn + recovery + canonical, gated by `@pytest.mark.validation`) |
| `examples/` | Worked examples (CLI fit, sample CSV) |
| `docs/` | mkdocs source (this site) |
| `e2e/` | Playwright E2E tests |

## Adding a documentation page

1. Drop a `.md` file under `docs/`.
2. Add it to the `nav:` in `mkdocs.yml`.
3. `mkdocs serve` to preview at http://127.0.0.1:8000.
4. Commit + push — the `Documentation` GitHub Actions workflow will rebuild + redeploy.

## Adding a code change

1. Read the relevant ADR(s) in `docs/decisions/` — major design choices are
   captured there.
2. Open a PR. The CI runs unit tests + lint + format check on Python 3.11 / 3.12 / 3.13.
3. If your change adds a feature, also add at least one test under `tests/`.
4. If your change touches the EM math or a fit algorithm, add a validation
   test under `validation/` (cross-check against a known-good reference).

## Code style

- Python: `ruff` + `black` (configured in `pyproject.toml`). Both run in CI.
- TypeScript: `tsc --noEmit` strict mode. No separate linter configured.
- Tests: prefer integration tests over unit tests on small functions.
- Commits: conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `style:`,
  `refactor:`, `test:`). Squash-merge.

## Architectural decisions

The ADRs in `docs/decisions/` document every cross-cutting decision:

- ADR-0001: backend choice (hmmlearn patched vs pomegranate)
- ADR-0002: B web UI stack (React + Vite + Tailwind + ...)
- ADR-0003: backend abstraction (HMMBackend Protocol)
- ADR-0004: supervised training (Phase A.7)
- ADR-0005: per-state EmissionSpec (Phase A.8)
- ADR-0006: Dirichlet priors (Phase A.9)
- ADR-0007: GMM-NHMM (Phase A.10)

If you're making a similarly cross-cutting decision, please open a new ADR
following the same template.

## Reporting bugs

Open an issue with:

- What you expected
- What happened
- A minimal reproduction (CSV + topology YAML + version)
- Stack trace if applicable
