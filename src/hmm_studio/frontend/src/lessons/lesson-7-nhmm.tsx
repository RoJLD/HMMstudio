import { NhmmBreathing } from "../components/academy/NhmmBreathing";

export function Lesson7Nhmm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        A standard HMM has a <em>fixed</em> transition matrix. But many
        real systems have transition rules that change over time, driven by
        external variables — funding rates affect crypto regime switches,
        weather affects mood, season affects shopping behavior. NHMM
        (Non-homogeneous HMM) makes <code>A_ij</code> depend on covariates.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">The math</h2>
      <p className="text-slate-700 mb-4">
        Replace the fixed transition matrix with a function of covariates.
        The standard formulation is multinomial logistic regression per
        source state:
      </p>
      <pre className="bg-slate-50 border border-slate-200 rounded p-3 text-xs font-mono overflow-x-auto mb-4">
        {`A_ij(z_t) = exp(beta_ij^T * z_t) / SUM_{j'} exp(beta_{ij'}^T * z_t)

where z_t in R^P is the covariate vector at time t,
and beta_ij in R^P are the learned coefficients
(one set per source state i, one row per target state j).`}
      </pre>
      <p className="text-slate-700 mb-4">
        Setting <code>beta_iK = 0</code> makes the K-th state the reference for that source
        row's softmax. With P covariates and K states, you have{" "}
        <code>K * (K-1) * P</code> new parameters compared to a vanilla HMM.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Watch A(z) breathe</h2>
      <p className="text-slate-700 mb-4">
        Below: a 3-state regime model (bear / range / bull) with one
        scalar covariate <code>z</code>. As you drag the slider, the
        transition matrix re-renders. Notice how the bull-state self-loop
        gets stronger when <code>z</code> is positive, weaker when{" "}
        <code>z</code> is negative.
      </p>
      <NhmmBreathing />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">How it's fit</h2>
      <p className="text-slate-700 mb-4">
        hmm-studio uses a two-stage approach:
      </p>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Fit a standard HMM on the observations (ignore covariates).
          This gives a Viterbi state path.
        </li>
        <li>
          For each source state <code>i</code>, fit a multinomial
          logistic regression on <code>(z_t, next_state | state_t = i)</code>{" "}
          pairs from the Viterbi path. This gives the beta coefficients.
        </li>
      </ol>
      <p className="text-slate-700 mb-4">
        This is the <em>pragmatic</em> approach — it's not the joint EM
        (which would update transitions and emissions and beta jointly), but
        it captures the spirit and ships in under 100 lines of code. The
        joint EM is on the roadmap as a follow-up.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">When to use NHMM</h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          You have a credible <em>exogenous</em> driver of regime change
          (macro indicator, environmental signal, control variable).
        </li>
        <li>
          The covariate has predictive value beyond the observations
          themselves — otherwise a regular HMM is simpler and adequate.
        </li>
        <li>
          You want to do counterfactuals: "if z had been low at this
          moment, would we still have transitioned to state X?"
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700">
        Click "Try in editor" to load a preset. Upload a CSV with at least
        one extra column (your covariate), then in the Fit page click that
        column under "Covariates" before launching the fit. The Results
        page will show a slider for <code>t</code> that animates the
        learned <code>A(t)</code> just like the demo above — but with{" "}
        <em>your</em> data driving it.
      </p>
    </>
  );
}
