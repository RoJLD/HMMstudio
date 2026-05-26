import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson12HierarchicalHmm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Multi-scale sequences : a regime inside a regime
      </h2>
      <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-4 text-amber-900 text-sm">
        <strong>Theory-only lesson.</strong> Hierarchical HMM (Phase
        A.11) is <em>spec-drafted but not yet implemented</em> in{" "}
        <code>hmm-studio</code>. The code is gated on an explicit
        external signal (see{" "}
        <code>docs/specs/2026-05-22-phase-a11-hhmm.md</code>). This
        lesson teaches the concept and points at the canonical paper —
        the engine itself is not part of the current release.
      </div>
      <p className="text-slate-700 mb-4">
        Some sequences are <strong>multi-scale</strong> by nature.
        Speech : phonemes group into syllables, syllables group into
        words, words group into phrases. Handwriting : strokes group
        into characters, characters group into words. Music : notes
        group into motifs, motifs group into phrases.
      </p>
      <p className="text-slate-700 mb-4">
        A flat HMM treats every transition the same way. If you tried
        to model a 100 000-word transcript with one big HMM, the model
        wouldn't know that "word boundary" is a different kind of
        transition than "phoneme boundary inside a word" — it would
        average them together.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The HHMM idea
      </h2>
      <p className="text-slate-700 mb-4">
        Fine, Singer & Tishby (1998) defined the{" "}
        <strong>Hierarchical HMM</strong> : every state of a "top
        level" HMM is itself <em>another</em> HMM. Activate a top
        state, you enter its sub-HMM and run it until it emits a
        terminal symbol, then control returns to the top level which
        transitions to the next top state.
      </p>
      <p className="text-slate-700 mb-4">
        Two state types live side by side :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Production states</strong> — emit observations
          (leaves of the hierarchy).
        </li>
        <li>
          <strong>Internal / abstract states</strong> — emit a child
          sub-HMM rather than an observation. When the child's "end
          state" is reached, control bubbles back up.
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        The natural inference algorithm generalises forward-backward
        through the hierarchy. Fine et al. extend Baum-Welch as well
        — the math is heavier but follows the same EM template you
        met in Lesson 5.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Why <code>hmm-studio</code> hasn't shipped it
      </h2>
      <p className="text-slate-700 mb-4">
        Three reasons, in order of importance :
      </p>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>No external user has asked for it.</strong> Our
          scope discipline says "spec drafted, code gated until a
          professor, researcher, or paid user requests the feature".
          It keeps the surface area of the project honest.
        </li>
        <li>
          Implementation is ~3-4 weeks for a clean version, plus
          another 1-2 weeks of API + validation. Substantial.
        </li>
        <li>
          The use cases overlap heavily with{" "}
          <em>multi-resolution time-series</em> tasks where deep
          learning architectures (transformers, recurrent autoencoders)
          have eaten most of the market. HHMM remains relevant in
          interpretability-critical settings (where you need to inspect
          why an output happened) and in bioinformatics — niches that
          our user base doesn't currently cover.
        </li>
      </ol>
      <p className="text-slate-700 mb-4">
        If your project needs HHMM, file an issue at{" "}
        <a
          href="https://github.com/RoJLD/HMMstudio/issues"
          target="_blank"
          rel="noreferrer"
          className="text-indigo-600 hover:underline"
        >
          github.com/RoJLD/HMMstudio/issues
        </a>{" "}
        with your use case — we ship gated features when there's a
        real demand signal.
      </p>

      <FurtherReading
        references={[
          {
            label: "Fine, Singer & Tishby 1998",
            title:
              "The Hierarchical Hidden Markov Model : Analysis and Applications (Machine Learning 32)",
            url: "https://www.cs.princeton.edu/courses/archive/spr06/cos598C/papers/FineSingerTishby1998.pdf",
            note: "the canonical paper — start here",
          },
          {
            label: "Springer publisher PDF",
            title: "Same paper, publisher version",
            url: "https://link.springer.com/content/pdf/10.1023/A:1007469218079.pdf",
          },
        ]}
      />
    </>
  );
}
