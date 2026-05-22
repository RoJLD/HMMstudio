# Release checklist

When publishing a new version of hmm-studio:

## Pre-release

- [ ] Update version in:
  - `pyproject.toml`
  - `src/hmm_core/__init__.py`
  - `src/hmm_studio/__init__.py`
  - `src/hmm_studio/frontend/package.json`
  - `CITATION.cff` (also bump `date-released`)
- [ ] Add a new entry at the top of `CHANGELOG.md` following the Keep a
      Changelog format
- [ ] Confirm `pytest -q` is green
- [ ] Confirm `ruff check src/ tests/` and `black --check src/ tests/` are clean
- [ ] Confirm `python scripts/build_frontend.py` runs successfully
- [ ] Confirm `python -m build` produces both sdist and wheel
- [ ] Confirm the wheel includes `hmm_studio/server/static/*` (use `zipfile`)
- [ ] Smoke test the wheel in a fresh venv (`hmm-fit --help`, `hmm-studio --help`)

## Release

- [ ] Commit the version bump + CHANGELOG entry
- [ ] `git tag -a vMAJOR.MINOR.PATCH -m "..."` (annotated tag)
- [ ] `git push origin main && git push origin vMAJOR.MINOR.PATCH`
- [ ] GitHub Actions `release.yml` builds + publishes to PyPI (Trusted Publishing)
- [ ] Verify on PyPI: https://pypi.org/project/hmm-studio/
- [ ] Create a GitHub release from the tag with the CHANGELOG entry as body

## Post-release

- [ ] Bump versions to the next pre-release (e.g., 1.1.0-dev) in dev branch
- [ ] Update `docs/roadmap.md` to reflect what shipped
- [ ] Announce (Twitter / blog / lab Slack)
