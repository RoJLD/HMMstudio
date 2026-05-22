import { BaumWelchAnimation } from "../components/academy/BaumWelchAnimation";

export function Lesson5BaumWelch() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        Forward and Viterbi assume you already <strong>have</strong> the model
        — the transition matrix A, the initial distribution pi, the emission
        distributions per state. In the real world, you have <em>only</em>{" "}
        observations and want to <strong>learn</strong> the model from them.
        Baum-Welch (1970) is the algorithm for that.
      </p>
      <p className="text-slate-700 mb-4">
        Baum-Welch is <strong>Expectation-Maximization</strong> specialized to
        HMMs. You don't need to know the EM theory to use it, but knowing
        what's happening helps debug convergence problems.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Two steps, repeated</h2>
      <p className="text-slate-700 mb-4">
        Start with random parameters. Then repeat until convergence:
      </p>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>E-step</strong>: with the current parameters fixed, compute
          posterior probabilities over the hidden states for every time-step:{" "}
          <code>gamma_t(k) = P(z_t = k | O, model)</code> (forward-backward) and{" "}
          <code>xi_t(i, j) = P(z_t=i, z_(t+1)=j | O, model)</code>{" "}
          (pairwise).
        </li>
        <li>
          <strong>M-step</strong>: re-estimate the parameters using these
          soft assignments.{" "}
          <code>A_ij = SUM_t xi_t(i,j) / SUM_t gamma_t(i)</code>{" "}
          (proportion of transitions out of <code>i</code> that go to{" "}
          <code>j</code>). Emissions and pi get analogous updates.
        </li>
      </ol>
      <p className="text-slate-700 mb-4">
        Each iteration monotonically improves (or at least doesn't decrease)
        the log-likelihood. The algorithm converges to a <em>local</em>{" "}
        maximum — different random initializations can land at different
        local optima. That's why <code>init.strategy</code> matters.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Watch it converge</h2>
      <p className="text-slate-700 mb-4">
        Below is a pre-computed Baum-Welch trace on a synthetic dataset.
        Click play to step through the iterations. The log-likelihood is
        monotonically increasing; the transition matrix sharpens from
        diffuse to structured.
      </p>
      <BaumWelchAnimation />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Practical tips</h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Run multiple random initializations and keep the best by{" "}
          <code>log_likelihood</code>. hmm-studio's <code>random</code>{" "}
          init strategy does this implicitly when you re-fit with a new seed.
        </li>
        <li>
          Use <code>kmeans</code> init for emissions: it usually beats random
          and converges faster (10-50 iterations vs 100+).
        </li>
        <li>
          If log-lik stagnates early, the model may be under-capacity
          (try larger K) or over-capacity (try Dirichlet priors). The K-scan
          panel helps you decide.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700">
        Click "Try in editor" to load a small preset. Then upload any CSV
        from the <code>examples/</code> directory and watch Baum-Welch
        converge live on the Fit page.
      </p>
    </>
  );
}
