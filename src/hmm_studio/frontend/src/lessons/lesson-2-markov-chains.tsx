import { ProbabilitySimplex } from "../components/academy/ProbabilitySimplex";

export function Lesson2MarkovChains() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Before "hidden", just "Markov"
      </h2>
      <p className="text-slate-700 mb-4">
        Strip away the observations and you're left with a Markov chain:
        a sequence of states that depend only on the previous state. This
        is the engine inside an HMM.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The transition matrix
      </h2>
      <p className="text-slate-700 mb-4">
        For K states, the transition matrix is K×K. Row{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">i</code> gives the probabilities of going to each next state
        from state <code className="bg-slate-100 px-1 rounded text-sm">i</code>. Rows must sum to 1.
      </p>
      <p className="text-slate-700 mb-4">
        For 3 states, each row lives on a 2-simplex (a triangle). Drag the
        point inside the triangle below to see how the probabilities of
        transitioning to each of three states must always sum to 1.
      </p>
      <ProbabilitySimplex />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Forbidden transitions
      </h2>
      <p className="text-slate-700 mb-4">
        Sometimes you know that certain transitions can't happen. A speech
        phoneme can't go backwards. A device that breaks can't un-break. A
        cell that's differentiated can't undifferentiate. In hmm-studio,
        you mark this with the{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">allowed_transitions</code>{" "}
        field of your topology, and the EM loop enforces it.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Try it
      </h2>
      <p className="text-slate-700">
        Click "Try in editor" above to open a sample 3-state weather model.
        Add a forbidden transition (delete the edge from sunny to rainy
        directly) and see how the validator reacts.
      </p>
    </>
  );
}
