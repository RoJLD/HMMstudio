import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson10BayesianHmm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Beyond point estimates : the Bayesian view
      </h2>
      <p className="text-slate-700 mb-4">
        Baum-Welch returns <em>one</em> set of parameters — the maximum
        likelihood estimate. That's perfect for downstream prediction
        but tells you nothing about <strong>how confident</strong> the
        model is in those parameters. If you only saw the regime change
        twice in 1000 timesteps, your transition probability estimate
        is noisy ; a single number doesn't capture that.
      </p>
      <p className="text-slate-700 mb-4">
        Bayesian inference returns a <strong>posterior
        distribution</strong> over parameters. You get credible
        intervals on transmat rows, on emission means, on state
        durations — anything you can derive from the parameters.
        Useful for publication-grade uncertainty quantification, A/B
        testing of model variants, and posterior predictive checks
        ("does my model reproduce the observed regime persistence ?").
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        How <code>BayesianHMMBackend</code> works
      </h2>
      <p className="text-slate-700 mb-4">
        <code>hmm_core.backends.bayesian_backend.BayesianHMMBackend</code>{" "}
        implements the <code>HMMBackend</code> protocol using PyMC's
        NUTS sampler. Priors :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>transmat row</strong> ~ Dirichlet(1) — uniform over
          the simplex
        </li>
        <li>
          <strong>startprob</strong> ~ Dirichlet(1)
        </li>
        <li>
          <strong>means</strong> ~ Normal(0, 10) per state per
          feature
        </li>
        <li>
          <strong>sigmas</strong> ~ HalfNormal(5) per state per
          feature
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        Likelihood is computed via the forward algorithm in{" "}
        <code>pytensor.scan</code> (log-space, numerically stable).
        After sampling, the posterior mean drops into a
        <code>ConstrainedGaussianHMM</code> so the existing{" "}
        <code>decode</code> / <code>predict</code> / <code>score</code>{" "}
        machinery just works.
      </p>
      <p className="text-slate-700 mb-4">
        Full <code>arviz.InferenceData</code> is exposed on{" "}
        <code>backend.last_idata_</code> for credible intervals,
        posterior predictive checks, trace plots, and R-hat
        convergence diagnostics.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        When to reach for it
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          You're writing a paper and need <code>P(parameter ∈ ...)</code>{" "}
          statements, not just point estimates.
        </li>
        <li>
          You have a small dataset and want the model to express its
          uncertainty rather than overconfidently fit.
        </li>
        <li>
          You want posterior predictive checks — generate synthetic
          data from the fitted posterior and check it matches
          observed properties (regime durations, returns
          distribution).
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        When NOT to use it : if you just need fast point estimates,
        the frequentist path (default) is 10-100× quicker and
        equally accurate.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Setup
      </h2>
      <p className="text-slate-700 mb-4">
        Bayesian dependencies are opt-in (PyMC is ~150 MB) :
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>pip install "hmm-studio[bayesian]"</code>
      </pre>
      <p className="text-slate-700 mb-4">
        Then in code :
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`from hmm_core.backends import get_backend
backend = get_backend("bayesian")
result = backend.fit(topology, X, seed=42, ...)
# result.model is a ConstrainedGaussianHMM at the posterior mean
# backend.last_idata_ holds the full arviz InferenceData`}</code>
      </pre>
      <p className="text-slate-700 mb-4">
        See <code>notebooks/09_bayesian_hmm.ipynb</code> for a runnable
        example with credible intervals on a 3-state Gaussian model.
      </p>

      <FurtherReading
        references={[
          {
            label: "Damiano — Stan HMM tutorial",
            title:
              "A Tutorial on Hidden Markov Models using Stan (Bayesian HMM by hand)",
            url: "https://luisdamiano.github.io/stancon18/hmm_stan_tutorial.pdf",
            note: "best practical introduction to Bayesian HMMs",
          },
          {
            label: "arXiv 2509.17806",
            title: "Bayesian Non-Homogeneous Hidden Markov Models",
            url: "https://arxiv.org/pdf/2509.17806",
            note: "extends Bayesian HMM to covariate-driven transitions",
          },
          {
            label: "Murphy MLAPP Ch. 17-18",
            title:
              "Bayesian treatment of HMMs and State Space Models",
            url: "https://archive.org/details/machinelearningp0000murp",
          },
        ]}
      />
    </>
  );
}
