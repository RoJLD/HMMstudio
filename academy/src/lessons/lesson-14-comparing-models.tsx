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
        In a real unsupervised crypto regime-detection study, a plain{" "}
        <strong>GMM-HMM</strong> outperformed a more elaborate non-homogeneous HMM
        (NHMM) with covariate-driven transitions. More parameters bought a higher raw
        likelihood, but not a better penalized score. The lesson generalizes: start
        simple, and make each added ingredient earn its place.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Complexity must pay — and negative results count
      </h2>
      <p className="text-slate-700 mb-4">
        In the same study, a hand-built Skew-T emission — the heaviest piece of
        engineering — <em>degraded</em> the fit relative to a plain Student-t. That is
        not a failure to hide; it is information. A result that says “this extension
        does not help” is exactly as valuable as one that says it does, and it saves you
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
        shows them, but never crowns them “best by BIC”.
      </p>

      <div className="my-6 border-l-4 border-brand-300 bg-brand-50 px-4 py-3 rounded-r">
        <p className="text-sm text-slate-700">
          <strong>Case study credit.</strong> The empirical findings above are adapted
          from Nathan Berbinau's unsupervised crypto regime-detection research (
          <a
            href="https://github.com/NathanBerbinau"
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-700 hover:underline"
          >
            github.com/NathanBerbinau
          </a>
          ). We reuse the <em>methodology and its honest caveats</em> — not the
          out-of-scope models. Read the numbers as a qualitative case study: the
          benchmark used a single dataset and a metric that isn't defined across model
          families, so the takeaway is the <em>method</em>, not specific scores.
        </p>
      </div>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700">
        Open the{" "}
        <Link to="/compare" className="text-brand-700 hover:underline font-medium">
          Compare
        </Link>{" "}
        page, sweep an emission × K grid on your own data, and watch BIC / AIC / HQIC
        decide — including which “obvious upgrade” doesn't actually pay.
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
