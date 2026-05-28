import { FurtherReading } from "../components/academy/FurtherReading";
import { MarkovChainDemo } from "../components/academy/MarkovChainDemo";

export function Lesson1WhatIsAnHmm() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Why this matters
      </h2>
      <p className="text-slate-700 mb-4">
        Imagine you want to model the weather. Some days are sunny, some
        rainy, some cloudy. You don't know exactly which one is "in charge"
        from one day to the next, but you can <em>observe</em> what the
        weather looks like — temperature, humidity, whether it rains.
      </p>
      <p className="text-slate-700 mb-4">
        A <strong>Hidden Markov Model</strong> models this: an underlying
        sequence of <strong>hidden states</strong> (the regimes you can't
        see directly) that produce <strong>observations</strong> (what you
        actually measure). The hidden states transition over time according
        to a fixed pattern.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The ingredients
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>States</strong> — the hidden regimes (e.g. "sunny",
          "rainy"). You pick how many.
        </li>
        <li>
          <strong>Transition matrix</strong> A — how likely you are to go
          from one state to another.
        </li>
        <li>
          <strong>Emission distribution</strong> — given a state, what
          observations does it produce?
        </li>
        <li>
          <strong>Initial state probabilities</strong> π — which state
          does the system start in?
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Interactive demo
      </h2>
      <p className="text-slate-700 mb-4">
        Below is a tiny 3-state Markov chain. Click "Step" to advance the
        system; the highlighted node is the current state. Notice how, even
        with the same transition probabilities, the trajectory is random.
      </p>
      <MarkovChainDemo />

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        What's the "hidden" part?
      </h2>
      <p className="text-slate-700 mb-4">
        In a real HMM, you don't see the colored node. You only see the
        observations the state generates — e.g., a temperature reading.
        The job of the algorithms (forward, Viterbi, Baum-Welch) is to
        infer the hidden state sequence and the transition / emission
        parameters from the observations alone.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Next
      </h2>
      <p className="text-slate-700">
        The next lesson zooms in on the transition matrix — how to read
        it, how to design it, and what happens when you constrain it.
      </p>

      <FurtherReading
        references={[
          {
            label: "Rabiner 1989 §I-II",
            title: "A Tutorial on Hidden Markov Models",
            url: "https://www.cs.cmu.edu/~cga/behavior/rabiner1.pdf",
            note: "the canonical introduction; sets the notation everyone uses",
          },
          {
            label: "Toronto CS486 Lec 14",
            title: "Inference in Hidden Markov Models",
            url: "https://www.cs.toronto.edu/~axgao/cs486686_f21/lecture_notes/Lecture_14_on_Hidden_Markov_Models_1.pdf",
            note: "Russell-Norvig umbrella example, accessible",
          },
          {
            label: "Bishop PRML §13.1",
            title: "Pattern Recognition and Machine Learning, Ch. 13 Sequential Data",
            url: "http://www.cis.hut.fi/Opinnot/T-61.6020/2007/sequential_data.pdf",
            note: "HMM as a probabilistic graphical model",
          },
        ]}
      />
    </>
  );
}
