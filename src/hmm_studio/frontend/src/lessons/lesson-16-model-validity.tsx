import { Link } from "react-router-dom";
import { FurtherReading } from "../components/academy/FurtherReading";
import { ProgressCurve } from "../components/results/ProgressCurve";

// A real EM log-likelihood trace (monotone, plateauing) used to teach the
// healthy-convergence shape. Generated from a toy 2-state Gaussian fit.
const SAMPLE_TRACE = [
  -4200, -3120, -2440, -2055, -1882, -1812, -1786, -1776, -1772, -1770.8,
  -1770.4, -1770.25,
];

export function Lesson16ModelValidity() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        You fit an HMM, the held-out log-likelihood is terrible, and you don&apos;t
        know who to blame: the topology, the features, the emission, or just a bad
        initialization. Validity is not one number — it&apos;s a small set of{" "}
        <strong>assumptions</strong> and a <strong>checklist</strong> you run before,
        during, and after fitting. This lesson is that framework, wired to the exact
        diagnostics hmm-studio gives you.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The five validity assumptions
      </h2>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Stationarity</strong> — transitions and emissions don&apos;t change over time.</li>
        <li><strong>Markov property</strong> — the next state depends only on the current one (
          <Link to="/academy/lesson-1-what-is-an-hmm" className="text-brand-700 hover:underline">Lesson 1</Link>).</li>
        <li><strong>Conditional independence</strong> — observations are independent of the past given the state.</li>
        <li><strong>Finite, (roughly) known K</strong> — a fixed number of latent regimes actually exists.</li>
        <li><strong>Identifiability</strong> — parameters are recoverable / stable across initializations.</li>
      </ol>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Check before fitting</h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>Is the series stationary, or does the regime structure itself drift? Drift → consider an{" "}
          <Link to="/academy/lesson-7-nhmm" className="text-brand-700 hover:underline">NHMM</Link>.</li>
        <li>Plot the autocorrelation. Strong dependence beyond lag 1 violates Markov.</li>
        <li>Are your features genuinely predictive of the regime, and decorrelated? (
          <Link to="/academy/lesson-13-choosing-features" className="text-brand-700 hover:underline">Lesson 13</Link>.)</li>
        <li>Do you have a defensible K, or is it a guess? Start small and let validation grow it.</li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Watch during fitting — convergence
      </h2>
      <p className="text-slate-700 mb-4">
        Baum-Welch only finds a <em>local</em> optimum (
        <Link to="/academy/lesson-5-baum-welch" className="text-brand-700 hover:underline">Lesson 5</Link>).
        A healthy run shows the log-likelihood climbing monotonically and plateauing:
      </p>
      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <ProgressCurve history={SAMPLE_TRACE} />
      </div>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Did it converge?</strong> Check <code className="bg-slate-100 px-1 rounded text-sm">converged</code> and that the curve plateaued — not hit the iteration cap mid-climb.</li>
        <li><strong>Multiple inits.</strong> If your top-3 random seeds land at very different log-likelihoods, you have a local-optimum problem.</li>
        <li><strong>Parameter stability.</strong> Re-fit with another seed; a transmat that lurches is a fragile fit.</li>
        <li><strong>Label switching.</strong> States are unordered — a re-fit may relabel them. Order by an emission feature before comparing.</li>
      </ul>
      <p className="text-slate-700 mb-4">
        In hmm-studio this trace is now <strong>persisted</strong>: after a fit, the
        convergence curve stays on the results page (not just live during training).
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Diagnose after fitting</h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Decode and look.</strong> Viterbi/posterior state paths — are state durations plausible, or flickering every step (over-fragmentation / wrong K)?</li>
        <li><strong>Occupancy.</strong> A state with ~0 posterior occupancy means K is too large.</li>
        <li><strong>Residuals per state</strong> vs the fitted emission density — the emission diagnostic (
          <Link to="/academy/lesson-15-choosing-emission" className="text-brand-700 hover:underline">Lesson 15</Link>).</li>
        <li><strong>Held-out log-likelihood.</strong> Train-good / eval-bad → overfit or wrong emission. Both bad → topology/emission mismatch.</li>
        <li><strong>Interpretability.</strong> Do the learned transitions match domain intuition, or look random? Forbidden edges must be exactly zero (mask check).</li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">When NOT to use an HMM</h2>
      <p className="text-slate-700 mb-4">
        Intellectual honesty: HMMs win in a specific niche — small data, interpretable
        discrete regimes, audit/regulatory needs, teaching. They are the wrong tool when:
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li><strong>Regimes drift</strong> (non-stationary) → NHMM / switching models.</li>
        <li><strong>Long-range temporal dependence</strong> (ACF at lags ≫ 1) → autoregressive or state-space models.</li>
        <li><strong>Large data / NLP / long sequences</strong> → Transformers or modern SSMs (Mamba/S4) dominate.</li>
        <li><strong>No discrete regimes exist</strong> — the latent structure is continuous → a continuous latent-variable model.</li>
        <li><strong>Too few observations per parameter</strong> → Bayesian priors (
          <Link to="/academy/lesson-10-bayesian-hmm" className="text-brand-700 hover:underline">Lesson 10</Link>) or stronger constraints.</li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">A diagnostic workflow</h2>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>Fit with several initializations; record the top-3 log-likelihoods.</li>
        <li>Compare candidates by BIC/AIC/HQIC (
          <Link to="/academy/lesson-14-comparing-models" className="text-brand-700 hover:underline">Lesson 14</Link>) — never trust a single fit.</li>
        <li>Decode states; check durations, occupancy, and per-state means.</li>
        <li>Plot residuals per state against the fitted emission.</li>
        <li>Hold out 10–20% and check held-out log-likelihood (use a time-series split, not random KFold).</li>
        <li>Label regimes by an emission feature and confirm the ordering is stable across seeds.</li>
        <li>All pass → provisionally valid. Any fail → diagnose and iterate.</li>
      </ol>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700 mb-4">
        Load the preset attached to this lesson — a <strong>deliberately over-specified</strong>{" "}
        5-state model on data with only ~2 real regimes. Fit it and watch the red flags
        appear: a state collapses to near-zero occupancy, the convergence curve stalls,
        and BIC prefers fewer states. Then drop to K=2 and compare.
      </p>

      <FurtherReading
        references={[
          { label: "Bilmes 1998", title: "A Gentle Tutorial of the EM Algorithm", url: "https://f.hubspotusercontent40.net/hubfs/8111846/bilmes-em.pdf", note: "why EM log-likelihood is monotone and converges to a local optimum" },
          { label: "Celeux & Soromenho 1996", title: "An entropy criterion for assessing the number of clusters in a mixture model", url: "https://link.springer.com/article/10.1007/BF01246098", note: "label switching and choosing the number of components" },
          { label: "Murphy, MLAPP §16", title: "Machine Learning: A Probabilistic Perspective — HMMs", url: "https://probml.github.io/pml-book/book0.html", note: "HMM diagnostics and assumptions" },
          { label: "Academy bibliography", title: "Central sourced reference list for all Academy lessons", url: "https://github.com/RoJLD/HMMstudio/blob/main/docs/sources/academy-references.md" },
        ]}
      />
    </>
  );
}
