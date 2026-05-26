import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson8GmmHmm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        When one Gaussian per regime isn't enough
      </h2>
      <p className="text-slate-700 mb-4">
        The Gaussian HMM you met in earlier lessons assumes each hidden
        state emits observations from a <em>single</em> Gaussian
        distribution. That's clean and often enough — but real regimes
        sometimes have <strong>internal sub-modes</strong>.
      </p>
      <p className="text-slate-700 mb-4">
        Think of a "bear market" regime in finance : it isn't one shape.
        It mixes <em>grinding decline</em> (small daily losses, low
        volatility) and <em>panic crash</em> (large losses, vol spikes).
        Fit a single Gaussian to both and you get an over-wide
        distribution that captures neither. Fit a 2-component Gaussian
        mixture inside the bear state and each sub-mode gets its own
        mean and covariance.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Anatomy of a GMM-HMM
      </h2>
      <p className="text-slate-700 mb-4">
        For each state <code>k</code>, instead of one Gaussian
        <code>(μ_k, Σ_k)</code>, you have <code>M</code> components :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Mixture weights <code>w_k = (w_k1, …, w_kM)</code>, summing
          to 1.
        </li>
        <li>
          Per-component means <code>μ_km</code> and covariances{" "}
          <code>Σ_km</code>.
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        Combine that with covariate-driven transitions (NHMM, Lesson 7)
        and you get GMM-NHMM — what <code>hmm_core.gmm_nhmm</code>{" "}
        implements. The fit is 2-stage : GMM-HMM base on{" "}
        <code>X</code>, then per-state logistic regression of next
        state on covariates <code>Z</code>.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        When to reach for it
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          The data inside one regime is visibly multi-modal (cluster
          plots, density estimates).
        </li>
        <li>
          A single-Gaussian HMM has unreasonably large
          <code>Σ_k</code> — a tell-tale that EM is smoothing across
          sub-modes.
        </li>
        <li>
          BIC of a GMM-HMM (n_mix=2 or 3) is better than the Gaussian
          baseline — the extra parameters pay for themselves on
          real data.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Where to learn more
      </h2>
      <p className="text-slate-700 mb-4">
        See <code>notebooks/05_gmm_nhmm_submodes.ipynb</code> for a
        runnable example simulating 2 regimes × 2 sub-modes each, with
        a BIC comparison against the single-Gaussian baseline. The
        scope decisions (why 2-stage, what was rejected) live in{" "}
        <code>docs/decisions/0007-gmm-nhmm-scope.md</code>.
      </p>

      <FurtherReading
        references={[
          {
            label: "Reynolds — GMM tutorial",
            title: "Gaussian Mixture Models — the canonical introduction",
            url: "http://leap.ee.iisc.ac.in/sriram/teaching/MLSP_16/refs/GMM_Tutorial_Reynolds.pdf",
            note: "covers the EM update for GMM parameters in detail",
          },
          {
            label: "Columbia E6870 Lec 3",
            title:
              "Gaussian Mixture Models and Introduction to HMMs (speech recognition course)",
            url: "https://www.ee.columbia.edu/~stanchen/fall12/e6870/slides/lecture3.pdf",
          },
          {
            label: "Edinburgh ASR — HMM + GMM",
            title:
              "HMMs and Gaussian Mixture Models — the acoustic-model handout",
            url: "https://www.inf.ed.ac.uk/teaching/courses/asr/2016-17/asr03-hmmgmm-handout.pdf",
          },
          {
            label: "Rabiner 1989 §VI.A",
            title: "Continuous observation densities in HMMs (GMM emission)",
            url: "https://www.cs.cmu.edu/~cga/behavior/rabiner1.pdf",
          },
        ]}
      />
    </>
  );
}
