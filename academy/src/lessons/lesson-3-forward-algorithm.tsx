import { FurtherReading } from "../components/academy/FurtherReading";
import { Trellis } from "../components/academy/Trellis";

export function Lesson3ForwardAlgorithm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        Suppose you have a trained HMM and a sequence of observations.
        How likely is the sequence under the model? Naively summing over
        all 2^T possible state sequences is intractable. The{" "}
        <strong>forward algorithm</strong> computes this in O(T · K²) time
        using dynamic programming.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">The recursion</h2>
      <p className="text-slate-700 mb-4">
        Let <code>alpha_t(k) = P(o_1, ..., o_t, z_t = k)</code> — the joint probability
        of having seen the observations up to time <code>t</code> AND ending in
        state <code>k</code>. The recursion is:
      </p>
      <pre className="bg-slate-50 border border-slate-200 rounded p-3 text-xs font-mono overflow-x-auto mb-4">
        {`alpha_1(k) = pi_k * b_k(o_1)
alpha_t(k) = b_k(o_t) * SUM_i alpha_{t-1}(i) * A_{ik}     for t >= 2
P(O | model) = SUM_k alpha_T(k)`}
      </pre>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Interactive trellis</h2>
      <p className="text-slate-700 mb-4">
        Below is a tiny 2-state model with a 6-symbol observation sequence
        (R/B). Click "Step" to advance time; each column fills in based on
        the previous column.
      </p>
      <Trellis mode="forward" />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">What's happening</h2>
      <p className="text-slate-700 mb-4">
        At each step, the cell for state <code>k</code> at time <code>t</code>{" "}
        is the sum of "all the ways to get here" — from any predecessor state
        at time <code>t-1</code>, weighted by the transition and the emission
        probability of the current observation. The final answer{" "}
        <code>P(O | model)</code> is the sum of the last column.
      </p>
      <p className="text-slate-700 mb-4">
        Numerically, alpha values shrink exponentially as T grows (multiplications
        of probabilities). Production code uses <em>log-alpha</em> with the
        log-sum-exp trick — the math is the same, just stable.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Next</h2>
      <p className="text-slate-700">
        The next lesson swaps <code>SUM</code> for <code>max</code> in the
        recursion. The result is Viterbi: the most likely sequence of hidden
        states given the observations.
      </p>

      <FurtherReading
        references={[
          {
            label: "Rabiner 1989 §III.A",
            title: "Forward algorithm worked out step by step",
            url: "https://www.cs.cmu.edu/~cga/behavior/rabiner1.pdf",
          },
          {
            label: "Jurafsky SLP3 §A.2",
            title: "Speech and Language Processing — Forward algorithm with the Eisner ice-cream example",
            url: "https://web.stanford.edu/~jurafsky/slp3/A.pdf",
          },
          {
            label: "MIT 6.867 Lec 19",
            title: "Forward-backward derivation from scratch",
            url: "https://ocw.mit.edu/courses/6-867-machine-learning-fall-2006/bd962d39492e55697cfa6bb418ae1642_lec19.pdf",
          },
        ]}
      />
    </>
  );
}
