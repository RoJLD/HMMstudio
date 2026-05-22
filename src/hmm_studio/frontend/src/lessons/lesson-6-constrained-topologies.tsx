import { TopologyComparison } from "../components/academy/TopologyComparison";

export function Lesson6ConstrainedTopologies() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">Why this matters</h2>
      <p className="text-slate-700 mb-4">
        The default HMM assumption is <strong>ergodicity</strong> — every
        state can transition to every other state, including itself. For
        many real systems this is wrong:
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Speech recognition</strong>: phonemes don't go backwards
          inside a word (left-right topology with self-loops, "Bakis").
        </li>
        <li>
          <strong>Bioinformatics (profile HMMs)</strong>: domains have a
          forward-only structure with optional insert / delete states.
        </li>
        <li>
          <strong>Equipment lifecycle</strong>: "healthy" to "degraded" to
          "failed" — no recovery without intervention.
        </li>
        <li>
          <strong>Disease progression</strong>: many illnesses follow a
          monotone state ordering (no return to "presymptomatic" once
          symptoms appear).
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Side-by-side</h2>
      <p className="text-slate-700 mb-4">
        Below: the same 3-state HMM fit on the same data with two
        different topology constraints. Left = ergodic (default). Right =
        left-right (only forward edges). The forbidden cells (x) are
        forced to zero by the constraint mask.
      </p>
      <TopologyComparison />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">How it works in hmm-studio</h2>
      <p className="text-slate-700 mb-4">
        Each topology has an <code>allowed_transitions</code> list. Edges
        not in the list are forced to zero during every M-step:
      </p>
      <pre className="bg-slate-50 border border-slate-200 rounded p-3 text-xs font-mono overflow-x-auto mb-4">
        {`# Left-right Bakis (3 states, forward + self-loops only)
allowed_transitions:
  - [s0, s0]
  - [s0, s1]
  - [s1, s1]
  - [s1, s2]
  - [s2, s2]`}
      </pre>
      <p className="text-slate-700 mb-4">
        The implementation is mechanical: after each Baum-Welch M-step,
        the new <code>A</code> is multiplied element-wise by a binary{" "}
        mask, then each row is renormalized. Forbidden edges stay exactly
        zero through all iterations — no leakage.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Why this helps</h2>
      <p className="text-slate-700 mb-4">
        Beyond matching domain knowledge, constrained topologies:
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          Reduce the parameter count (fewer free probabilities to estimate)
          — better behavior on small datasets.
        </li>
        <li>
          Improve identifiability — state labels are less interchangeable
          when transitions have structural meaning.
        </li>
        <li>
          Speed up convergence — EM has fewer dimensions to explore.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">Try it</h2>
      <p className="text-slate-700">
        Click "Try in editor" to load a 4-state left-right topology. Try
        deleting one of the forward edges and watch the live validation
        catch the disconnected state.
      </p>
    </>
  );
}
