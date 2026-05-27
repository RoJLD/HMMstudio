# Contributors

## Maintainer

- **Robin Denis** — author & maintainer.

## Research that informed hmm-studio

- **Nathan Berbinau** — <https://github.com/NathanBerbinau>

  Several in-scope features were inspired by, or adapted from, Nathan's
  unsupervised crypto regime-detection research
  (`Experiment.Crypto.2026S1.NathanBerbinau`). In particular:

  - the **HQIC** information criterion (from his `ModelFinder`);
  - the **model-variant comparison** direction — the `hmm-fit compare` CLI and
    the `/compare` web page — which is the HMM-only slice of his
    `Model_Selection`;
  - the **Giudici (2020) 3-regime preset** and regime-labelling-by-feature-mean
    (`hmm_core.regimes`);
  - **unsupervised feature selection** by mutual-information clustering
    (`hmm_core.features`) — the scikit-learn-NMI form of his feature-selection
    approach;
  - the **Student-t emissions** scope decision (`docs/decisions/0014-…`).

  Nathan's empirical case study — that a simple GMM-HMM can outperform more
  elaborate variants, that added complexity must justify itself, and that
  log-likelihood is **not** comparable across different model families —
  also informs hmm-studio's model-selection material and the comparability
  rule built into `/compare`.

  > Scope note: Nathan's continuous-latent-state models (rSLDS, and the Skew-T
  > `ssm` extensions) were deliberately **not** adopted — they fall outside
  > hmm-studio's HMM scope (see `docs/decisions/`). This is a scope decision,
  > not a judgement on the quality of the work.
