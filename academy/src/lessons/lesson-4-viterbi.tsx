import { FurtherReading } from "../components/academy/FurtherReading";
import { Trellis } from "../components/academy/Trellis";

export function Lesson4Viterbi() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        Forward gives you a <strong>score</strong>: how likely is this sequence
        of observations? Viterbi gives you a <strong>decoding</strong>: what
        sequence of hidden states most likely produced these observations? In
        practice this is what you want when you say "the model says the system
        was in state <code>vol</code> from t=200 to t=350".
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">The recursion</h2>
      <p className="text-slate-700 mb-4">
        Replace the sum with a max. Let{" "}
        <code>delta_t(k) = max P(z_1..z_t, o_1..o_t | z_t=k)</code>.
        Track which predecessor gave that max in <code>psi_t(k)</code>.
      </p>
      <pre className="bg-slate-50 border border-slate-200 rounded p-3 text-xs font-mono overflow-x-auto mb-4">
        {`delta_1(k) = pi_k * b_k(o_1)
delta_t(k) = b_k(o_t) * max_i delta_{t-1}(i) * A_{ik}     for t >= 2
psi_t(k)   = argmax_i delta_{t-1}(i) * A_{ik}
z*_T       = argmax_k delta_T(k)
z*_t       = psi_{t+1}(z*_{t+1})                           backtrace from T-1 to 1`}
      </pre>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Interactive trellis</h2>
      <p className="text-slate-700 mb-4">
        Same trellis as the forward algorithm, but with{" "}
        <code>max</code> instead of <code>SUM</code>. After you reach{" "}
        <code>t = T-1</code>, the backtrace path is highlighted in green —
        that's the most likely state sequence.
      </p>
      <Trellis mode="viterbi" />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Same DP, different operation</h2>
      <p className="text-slate-700 mb-4">
        Forward and Viterbi share the same trellis structure. The DP is
        identical except for sum-vs-max. This is a recurring pattern —{" "}
        <em>semiring substitution</em> — that shows up across many algorithms
        (shortest path, max-flow, etc.).
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700">
        Click "Try in editor" to load a 3-state weather model. Upload your
        own short observation sequence, fit it, and inspect the Viterbi
        path on the Results page.
      </p>

      <FurtherReading
        references={[
          {
            label: "Rabiner 1989 §III.B",
            title: "Viterbi algorithm — backpointer construction",
            url: "https://www.cs.cmu.edu/~cga/behavior/rabiner1.pdf",
          },
          {
            label: "Jurafsky SLP3 §A.4",
            title: "Viterbi explained for POS tagging",
            url: "https://web.stanford.edu/~jurafsky/slp3/A.pdf",
          },
          {
            label: "Bilmes 1998 §6",
            title: "Viterbi inside the EM framework — same recursion, different operator",
            url: "https://www.cs.cmu.edu/~aarti/Class/10701/readings/gentle_tut_HMM.pdf",
          },
        ]}
      />
    </>
  );
}
