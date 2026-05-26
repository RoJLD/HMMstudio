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

---

## Outstanding for v1.1.0 (2026-05-23)

The `v1.1.0` tag was pushed on 2026-05-23 and the `release.yml` workflow
**built the wheel successfully but the publish step failed** because the
PyPI Trusted Publisher has never been registered for this repo. The wheel
artifact is on the GitHub Actions run but not on PyPI.

**To finish the v1.1.0 release** (do once, then every future tag publishes
automatically):

1. Go to <https://pypi.org/manage/account/publishing/>
2. Add a **Pending Publisher** with:
   - PyPI Project Name: `hmm-studio`
   - Owner: `RoJLD`
   - Repository name: `HMMstudio`
   - Workflow filename: `release.yml`
   - Environment name: *(leave blank)*
3. Open the failed run at
   <https://github.com/RoJLD/HMMstudio/actions/runs/26445194484>
4. Click **Re-run failed jobs** (re-runs only `publish`; `build` is cached)
5. Verify: `pip install hmm-studio==1.1.0` in a fresh venv
6. Create a GitHub Release at
   <https://github.com/RoJLD/HMMstudio/releases/new?tag=v1.1.0>
   with the `[1.1.0]` CHANGELOG entry as body

If step 4 fails again, inspect the run logs for the OIDC / Trusted
Publisher error — usually it's a typo in the Pending Publisher form.
