import { Link } from "react-router-dom";
import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson15ChoosingEmission() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        When the emission is wrong
      </h2>
      <p className="text-slate-700 mb-4">
        Your transitions are clean, your features are decorrelated, your K is
        sensible — and yet held-out log-likelihood collapses. The culprit is often the{" "}
        <strong>emission distribution</strong> : the family chosen to model{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">p(y | z)</code> simply
        does not fit the shape of the data inside each regime.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Symptoms of a wrong emission
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Held-out log-likelihood collapses</strong> with very high variance
          between cross-validation folds. A Gaussian assigns near-zero density to tail
          observations ; one fat-tailed fold can move the LL by hundreds of nats.
        </li>
        <li>
          <strong>Train LL is fine but eval LL is catastrophic.</strong> The model
          fits the bulk and is destroyed by the tails — the classic
          mismatched-family signature.
        </li>
        <li>
          <strong>Residuals per state don&apos;t match the assumed density.</strong> A
          heavy-tailed residual histogram against a fitted Gaussian curve is the
          clearest visual diagnostic.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Diagnostic recipe
      </h2>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>Fit the model, then decode states (Viterbi or posterior).</li>
        <li>
          For each state, plot the histogram of observed values assigned to that
          state, overlaid with the fitted emission density.
        </li>
        <li>
          If the visual mismatch is flagrant — or if held-out LL/obs has a standard
          deviation much larger than its mean — the emission family is the suspect.
        </li>
      </ol>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The remedy inside hmm-studio : GMM-HMM
      </h2>
      <p className="text-slate-700 mb-4">
        The native remedy in the app is to switch from a single Gaussian per state to
        a <strong>mixture of Gaussians</strong> (GMM-HMM). With a handful of
        components per state, the mixture can mimic heavier tails and multi-modal
        regimes that a single Gaussian cannot capture. See{" "}
        <Link
          to="/academy/lesson-8-gmm-hmm"
          className="text-brand-700 hover:underline"
        >
          Lesson 8 — GMM-HMM
        </Link>{" "}
        for the full story, and the topology preset attached to this lesson for a
        ready-to-fit example.
      </p>
      <p className="text-slate-700 mb-4">
        Conceptually, a GMM is itself a basis-function decomposition of densities — a
        weighted sum of Gaussian kernels, parallel to how a Fourier series decomposes
        a periodic signal into sinusoids. Both are{" "}
        <strong>universal approximators</strong> in their domain : enough Gaussian
        components can approximate any continuous density arbitrarily well. The
        practical difference : Gaussians aren&apos;t orthogonal (unlike sinusoids),
        so fitting needs EM rather than a closed-form projection, and the mixture
        weights must lie on the probability simplex.
      </p>

      <p className="text-slate-700 mb-4">
        Caveat : a GMM with Gaussian components is still a sum of{" "}
        <em>thin-tailed</em> densities. It approximates fat tails by spending
        components on the tails, which costs parameters. For genuinely heavy-tailed
        data, a proper heavy-tailed emission is more parsimonious — but those don&apos;t
        yet live in hmm-studio (see below).
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Beyond GMM</h2>
      <p className="text-slate-700 mb-4">
        If even GMM isn&apos;t enough, the research literature offers stronger emission
        families. Ranked by the evidence base for our regime (n ≈ a few thousand,
        low-dimensional, heavy-tailed financial returns) :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Multivariate skew-T mixture</strong> — strict, low-risk upgrade
          from Student-T. Handles heavy tails AND asymmetry, with an exact EM
          algorithm (no Monte Carlo). <em>Recommendation #1.</em>
        </li>
        <li>
          <strong>Generalized Hyperbolic (GH) HMM</strong> — nests Student-T, NIG and
          VG as special cases. Published specifically for multivariate financial
          returns, with penalized EM and L1 on state-specific precisions.{" "}
          <em>Recommendation #2.</em>
        </li>
        <li>
          <strong>Normalizing flows as emission</strong> (FlowHMM and variants) —
          architecturally viable with an EM + SGD hybrid M-step. But no peer-reviewed
          evidence they beat Student-T on financial held-out LL at n ≈ 3500, and
          neural density estimators overfit severely under MLE with scarce data.{" "}
          <em>Defer.</em>
        </li>
      </ul>

      <div className="my-6 border-l-4 border-brand-300 bg-brand-50 px-4 py-3 rounded-r">
        <p className="text-sm text-slate-700">
          <strong>Case study.</strong> On a daily ETH dataset (4 post-correlation
          features, ~3500 observations), a Gaussian HMM produces LL/obs around −200
          to −400 with huge variance — its tails are catastrophic on held-out folds.
          A Student-T HMM in the same setup gives LL/obs ≈ −6.3 stably. A
          non-homogeneous HMM with the same Student-T emission adds essentially
          nothing. Skew-T (single, not mixture) underperforms plain Student-T. The
          driver is the emission, not the transition structure. (Re-benchmark in{" "}
          <code>Projet_Robin/benchmark/</code> of the sibling crypto experiment repo.)
        </p>
      </div>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700 mb-4">
        Open the topology preset attached to this lesson : a 3-state GMM-HMM with 3
        mixture components per state on 2D features. Fit it, decode states, and
        inspect the residuals per state. If your data is heavy-tailed, the GMM
        components will cluster around the tails.
      </p>

      <FurtherReading
        references={[
          {
            label: "Lee & McLachlan 2011",
            title:
              "Finite mixtures of multivariate skew t distributions — exact EM",
            url: "https://arxiv.org/pdf/1109.4706",
            note: "the recommended strict upgrade from Student-T",
          },
          {
            label: "Foroni, Merlo & Petrella 2024",
            title:
              "Hidden Markov graphical models with state-dependent generalized hyperbolic distributions",
            url: "https://arxiv.org/pdf/2412.03668",
            note: "GH HMM applied to multivariate financial returns",
          },
          {
            label: "FlowHMM (NeurIPS 2022)",
            title: "Flow-based HMM emissions trained by hybrid EM + SGD",
            url: "https://proceedings.neurips.cc/paper_files/paper/2022/file/39c5871aa13be86ab978cba7069cbcec-Paper-Conference.pdf",
            note: "feasible architecture, but no financial held-out evidence at small n",
          },
          {
            label: "Rothfuss et al. (ICLR 2020)",
            title:
              "Noise regularization for conditional density estimation",
            url: "https://openreview.net/pdf?id=rygtPhVtDS",
            note: "documents the overfitting failure mode of neural density estimators at small sample size",
          },
          {
            label: "Academy bibliography",
            title: "Central sourced reference list for all Academy lessons",
            url: "https://github.com/RoJLD/HMMstudio/blob/main/docs/sources/academy-references.md",
          },
        ]}
      />
    </>
  );
}
