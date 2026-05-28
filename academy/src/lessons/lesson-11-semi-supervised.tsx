import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson11SemiSupervised() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Between unsupervised and supervised
      </h2>
      <p className="text-slate-700 mb-4">
        Two earlier lessons covered the extremes :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Unsupervised</strong> (Lesson 5, Baum-Welch) — no
          labels, EM discovers the regimes from data alone.
        </li>
        <li>
          <strong>Supervised</strong> (Phase A.7, not its own lesson)
          — every observation has its state label. Closed-form MLE,
          one pass, no EM.
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        Real datasets often sit in between : a domain expert annotated
        100 timesteps out of 10 000 by hand, the rest are unlabelled.
        Throwing the labels away (pure Baum-Welch) wastes information.
        Asking the expert to label everything is infeasible. Enter{" "}
        <strong>semi-supervised training</strong>.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The API : NaN or -1 as "unlabelled"
      </h2>
      <p className="text-slate-700 mb-4">
        <code>hmm_core.fit</code> accepts a <code>states</code>{" "}
        argument. Pass a NaN-bearing float array (or an int array with
        <code>-1</code> sentinels) to trigger the semi-supervised
        path :
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`from hmm_core.fit import fit
import numpy as np

states = np.full(len(X), np.nan)
states[100:200] = 0       # expert labelled these as state 0
states[500:600] = 2       # ... and these as state 2
# Everything else is NaN -> unlabelled

result = fit(topology, X, states=states, seed=42)
# EM runs with a clamped E-step :
#   labelled t  -> log P(obs | state != label[t]) = -inf
#   unlabelled t -> standard forward-backward`}</code>
      </pre>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        How the clamp works
      </h2>
      <p className="text-slate-700 mb-4">
        The trick is simple : at every labelled position{" "}
        <code>t</code>, force <code>P(obs[t] | state = k) = 0</code>{" "}
        for every <code>k ≠ label[t]</code>. Forward-backward then
        naturally produces <code>α[t][k] = 0</code> for the wrong
        states, so the responsibility γ collapses to a one-hot at the
        labelled state. EM continues normally on the rest.
      </p>
      <p className="text-slate-700 mb-4">
        Concretely, each <code>Constrained*HMM</code> class overrides
        hmmlearn's <code>_compute_log_likelihood</code> to inject{" "}
        <code>-inf</code> at the forbidden state for labelled
        timesteps. The implementation is a small mixin in{" "}
        <code>src/hmm_core/fit/_base.py</code>.
      </p>
      <p className="text-slate-700 mb-4">
        Initial parameters come from the supervised MLE computed on
        the labelled subset alone — gives EM a meaningful warm start
        instead of random initialization.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        When to use it
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Bioinformatics : a few sequences with ground-truth annotation
          plus thousands of unlabelled ones. Standard use case from the
          Durbin et al. tradition.
        </li>
        <li>
          Crypto / finance : a few obvious regime boundaries you know
          for sure (e.g., a regulator-flagged date), the rest left for
          EM to discover.
        </li>
        <li>
          Pre-segmented prefix : the first N timesteps of a long
          sequence were hand-checked, EM extends the partition.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Edge cases worth knowing
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>All labelled</strong> → falls back to the closed-form
          supervised path (no EM).
        </li>
        <li>
          <strong>All unlabelled</strong> → raises ; use{" "}
          <code>fit(topology, X)</code> without <code>states</code>{" "}
          instead.
        </li>
        <li>
          <strong>Mask violation</strong> — if two adjacent labelled
          positions claim a transition that the topology forbids, the
          fit raises <code>ValueError</code>. Either relax the topology
          or fix the labels.
        </li>
        <li>
          <strong>Multi-sequence</strong> support — pass{" "}
          <code>lengths=[…]</code> as usual. The clamp segments
          correctly across sequence boundaries.
        </li>
      </ul>

      <FurtherReading
        references={[
          {
            label: "Tamposis et al. 2019",
            title:
              "Semi-supervised learning of HMMs for biological sequence analysis (Bioinformatics)",
            url: "https://academic.oup.com/bioinformatics/article/35/13/2208/5184961",
            note: "the closest published equivalent to what hmm-studio implements",
          },
          {
            label: "BMC Bioinformatics 2021",
            title:
              "A new algorithm to train HMMs for biological sequences with partial labels",
            url: "https://ncbi.nlm.nih.gov/pmc/articles/PMC7995745",
          },
          {
            label: "Springer — Partially-Hidden Markov Models",
            title:
              "Generalised framework subsuming supervised / unsupervised / semi-supervised cases",
            url: "https://link.springer.com/chapter/10.1007/978-3-642-29461-7_42",
          },
        ]}
      />
    </>
  );
}
