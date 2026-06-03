import { Link } from "react-router-dom";
import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson14ComparingModels() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Does complexity pay?
      </h2>
      <p className="text-slate-700 mb-4">
        It is tempting to assume that a richer model — more states, covariate-driven
        transitions, fancier emissions — is a better model. It often isn't. The only
        honest way to know is to <strong>benchmark</strong>: fit several candidates on
        the same data and rank them by an information criterion (BIC / AIC / HQIC) that
        already charges for extra parameters.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The simplest model often wins
      </h2>
      <p className="text-slate-700 mb-4">
        In a first pass of this study, a plain <strong>GMM-HMM</strong> appeared to
        outperform a non-homogeneous HMM (NHMM) — but that headline did not survive a
        clean re-benchmark. The original comparison mixed two libraries, used K=2 for
        the GMM-HMM but K=3 for the others, and applied a per-sample normalization by
        hand outside the script. A re-run with a single library, the same K, the same
        features, and time-series cross-validation showed the parsimony lesson still
        holds — but on a different axis : it's the{" "}
        <strong>emission distribution</strong> that dominates (heavy-tailed Student-T
        crushes Gaussian on held-out log-likelihood), while{" "}
        <strong>non-homogeneous transitions add essentially nothing</strong> over the
        homogeneous Student-T HMM. Start simple, and make each added ingredient earn
        its place — but be honest about <em>which</em> ingredient.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Complexity must pay — and negative results count
      </h2>
      <p className="text-slate-700 mb-4">
        In the same study, a hand-built Skew-T emission — the heaviest piece of
        engineering — <em>degraded</em> the fit relative to a plain Student-t. That is
        not a failure to hide; it is information. A result that says "this extension
        does not help" is exactly as valuable as one that says it does, and it saves you
        from shipping needless complexity.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        You can't compare everything
      </h2>
      <p className="text-slate-700 mb-4">
        Here is the subtle trap. A log-likelihood is only comparable between models that
        describe the <em>same</em> thing. A plain HMM and a GMM/Poisson HMM all model{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">P(X)</code> — comparable. But
        an NHMM models{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">P(X | Z)</code> (conditioned
        on covariates), and a switching linear dynamical system (rSLDS) lives in a
        continuous latent space entirely. Their likelihoods are on different scales —
        ranking them by a single BIC is meaningless.
      </p>
      <p className="text-slate-700 mb-4">
        This is exactly why hmm-studio's{" "}
        <Link to="/compare" className="text-brand-700 hover:underline">
          Compare
        </Link>{" "}
        tool only ranks <code className="bg-slate-100 px-1 rounded text-sm">P(X)</code>{" "}
        candidates and flags NHMM / Factorial models as{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">comparable=False</code>: it
        shows them, but never crowns them &ldquo;best by BIC&rdquo;.
      </p>

      <p className="text-slate-700 mb-4">
        The first version of this case study tripped on four concrete pitfalls, worth
        knowing : (i) mixing two libraries with different likelihood conventions in one
        table ; (ii) comparing in-sample vs hold-out scores ; (iii) applying a
        per-observation normalization by hand outside the script — invisible to anyone
        reading the code ; (iv) evaluating a held-out predictive density under a
        Gaussian approximation for models with heavy-tailed emissions, which mismodels
        the tails and makes the metric non-comparable across families. Fixing all four
        turned the original &ldquo;GMM-HMM wins, NHMM +60%&rdquo; claim into &ldquo;emission dominates,
        transitions don&apos;t&rdquo;.
      </p>

      <div className="my-6 border-l-4 border-brand-300 bg-brand-50 px-4 py-3 rounded-r">
        <p className="text-sm text-slate-700">
          <strong>Case study credit.</strong> The empirical findings above are adapted
          from Nathan Berbinau&apos;s unsupervised crypto regime-detection research, with a
          methodology re-benchmark in the sibling crypto-experiment repo
          (<code>Projet_Robin/benchmark/</code>). We reuse the methodology, the{" "}
          <strong>honest re-benchmark</strong>, and its <strong>corrected</strong>{" "}
          negative results — not the out-of-scope models. Read the numbers as a
          qualitative case study : a single dataset, several metrics not all
          comparable across model families.
        </p>
      </div>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700 mb-4">
        Open the{" "}
        <Link to="/compare" className="text-brand-700 hover:underline font-medium">
          Compare
        </Link>{" "}
        page, sweep an emission × K grid on your own data, and watch BIC / AIC / HQIC
        decide — including which &ldquo;obvious upgrade&rdquo; doesn&apos;t actually pay.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">See also</h2>
      <p className="text-slate-700 mb-4">
        <Link
          to="/academy/lesson-15-choosing-emission"
          className="text-brand-700 hover:underline"
        >
          Lesson 15 — Choosing the emission distribution
        </Link>{" "}
        : the diagnostic recipe and the upgrade ladder once you know the emission is
        the bottleneck.
      </p>

      <p className="text-slate-700 mb-4">
        Comparison tells you which model wins; validity tells you whether the winner is
        trustworthy at all. See{" "}
        <Link to="/academy/lesson-16-model-validity" className="text-brand-700 hover:underline">
          Lesson 16 — Model validity
        </Link>.
      </p>

      <FurtherReading
        references={[
          {
            label: "Nathan Berbinau — crypto regime research",
            title: "Unsupervised regime detection: GMM-HMM / NHMM / rSLDS benchmark",
            url: "https://github.com/NathanBerbinau",
            note: "The case study this lesson draws on (methodology + honest negative results)",
          },
          {
            label: "Giudici, Pagnottoni & Polinesi (2020)",
            title: "Network models to enhance automated cryptocurrency portfolio management",
            url: "https://doi.org/10.3389/frai.2020.00022",
            note: "3-regime crypto framing related to the bundled Giudici preset",
          },
        ]}
      />
    </>
  );
}
