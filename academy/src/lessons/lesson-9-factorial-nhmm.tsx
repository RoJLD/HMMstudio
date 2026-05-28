import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson9FactorialNhmm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        When regimes have multiple independent dimensions
      </h2>
      <p className="text-slate-700 mb-4">
        Earlier lessons treated the hidden state as a <em>single</em>{" "}
        categorical variable — at each time <code>t</code>, the system
        is in exactly one of <code>K</code> states. Many real systems
        don't fit that shape.
      </p>
      <p className="text-slate-700 mb-4">
        A market has a <strong>trend</strong> dimension (up / sideways
        / down) AND a <strong>volatility</strong> dimension (low /
        high). They're driven by different forces. Modeling them as a
        flat 6-state HMM forces EM to enumerate every (trend, vol)
        combination and learn a full <code>6 × 6</code> transition
        matrix — even though the dynamics are really{" "}
        <code>3 × 3</code> for trend and <code>2 × 2</code> for vol,
        completely separate.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Factorial NHMM : D parallel chains
      </h2>
      <p className="text-slate-700 mb-4">
        A <strong>Factorial HMM</strong> (Ghahramani & Jordan 1997)
        decomposes the hidden state as a tuple{" "}
        <code>(z^1, z^2, …, z^D)</code>, one variable per chain. Each
        chain has its own transition dynamics. The joint state space
        has size <code>K_joint = ∏ K_d</code>, but the
        <em>parameter count</em> drops from{" "}
        <code>K_joint²</code> to <code>Σ_d K_d²</code>.
      </p>
      <p className="text-slate-700 mb-4">
        Concrete example with D = 3 chains and K_d = 3 each :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Joint HMM transition params : <code>27² = 729</code>
        </li>
        <li>
          Factorial : <code>3 · 3² = 27</code>
        </li>
        <li>
          <strong>27× parameter savings</strong> — same expressivity
          when the chains are genuinely independent.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        How we ship it
      </h2>
      <p className="text-slate-700 mb-4">
        <code>hmm_core.factorial_nhmm</code> uses a 2-stage
        decomposition (same pattern as GMM-NHMM in Lesson 8) :
      </p>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Standard Gaussian HMM on the joint product space{" "}
          <code>K_joint</code> (hard cap at 27 for tractability).
        </li>
        <li>
          Project joint Viterbi to per-chain trajectories via{" "}
          <code>np.unravel_index</code>. Fit one NHMM logit per chain
          on its own covariates.
        </li>
      </ol>
      <p className="text-slate-700 mb-4">
        Each chain exposes <code>decode_chain(X, chain_name)</code>{" "}
        for per-chain Viterbi and <code>A_t(chain_name)</code> for
        the time-varying per-chain transition matrix.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Where to learn more
      </h2>
      <p className="text-slate-700 mb-4">
        See <code>notebooks/06_factorial_nhmm_multifactor.ipynb</code>{" "}
        for a worked trend × vol example. The 2-stage rationale and
        rejected alternatives (joint-logit expansion) are in{" "}
        <code>docs/specs/2026-05-22-phase-a13-factorial-nhmm.md</code>.
      </p>

      <FurtherReading
        references={[
          {
            label: "Ghahramani & Jordan 1997",
            title: "Factorial Hidden Markov Models (Machine Learning 29)",
            url: "https://dspace.mit.edu/bitstream/handle/1721.1/7188/AIM-1561.pdf?sequence=2",
            note: "the seminal paper introducing the factorial decomposition",
          },
          {
            label: "Springer version",
            title:
              "Factorial Hidden Markov Models — official publication",
            url: "https://link.springer.com/article/10.1023/A:1007425814087",
          },
        ]}
      />
    </>
  );
}
