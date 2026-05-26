import type { ReactNode } from "react";
import type { NotebookRef } from "../components/academy/NotebookLink";
import { Lesson1WhatIsAnHmm } from "./lesson-1-what-is-an-hmm";
import { Lesson2MarkovChains } from "./lesson-2-markov-chains";
import { Lesson3ForwardAlgorithm } from "./lesson-3-forward-algorithm";
import { Lesson4Viterbi } from "./lesson-4-viterbi";
import { Lesson5BaumWelch } from "./lesson-5-baum-welch";
import { Lesson6ConstrainedTopologies } from "./lesson-6-constrained-topologies";
import { Lesson7Nhmm } from "./lesson-7-nhmm";
import { Lesson8GmmHmm } from "./lesson-8-gmm-hmm";
import { Lesson9FactorialNhmm } from "./lesson-9-factorial-nhmm";
import { Lesson10BayesianHmm } from "./lesson-10-bayesian-hmm";
import { Lesson11SemiSupervised } from "./lesson-11-semi-supervised";
import { Lesson12HierarchicalHmm } from "./lesson-12-hierarchical-hmm";

export interface LessonMeta {
  id: string;
  title: string;
  estimatedMinutes: number;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  description: string;
  status: "published" | "planned";
  // Optional: a YAML topology preset to load in the editor when the user
  // clicks "Try in editor" from this lesson.
  presetTopologyYaml?: string;
  // Optional: a Jupyter notebook companion. Rendered as a launcher card
  // (Binder / Colab / GitHub / Download) at the bottom of the lesson.
  notebookLink?: NotebookRef;
  // The rendered React component for the lesson body (only for "published" lessons)
  content?: () => ReactNode;
}

export const LESSONS: LessonMeta[] = [
  {
    id: "lesson-1-what-is-an-hmm",
    title: "What is an HMM?",
    estimatedMinutes: 10,
    difficulty: "Beginner",
    description:
      "A gentle intro to hidden Markov models: hidden states, observations, transitions, emissions. No math required.",
    status: "published",
    content: Lesson1WhatIsAnHmm,
    notebookLink: {
      filename: "01_quickstart.ipynb",
      title: "Quickstart — declare, fit, decode in 4 lines",
      description:
        "A 30-second tour : a 3-state Gaussian topology, Baum-Welch fit, Viterbi decode, plus a left-right constrained variant.",
    },
  },
  {
    id: "lesson-2-markov-chains",
    title: "Markov chains — the engine inside",
    estimatedMinutes: 12,
    difficulty: "Beginner",
    description:
      "Before HMMs are hidden, they're Markov chains. Build intuition for the transition matrix interactively.",
    status: "published",
    content: Lesson2MarkovChains,
    presetTopologyYaml: `name: lesson_2_demo
n_states: 3
state_names: [sunny, cloudy, rainy]
emission:
  type: multinomial
  n_symbols: 3
allowed_transitions:
  - [sunny, sunny]
  - [sunny, cloudy]
  - [cloudy, cloudy]
  - [cloudy, sunny]
  - [cloudy, rainy]
  - [rainy, rainy]
  - [rainy, cloudy]
startprob: uniform
init: {strategy: uniform, seed: 0}
fit: {algorithm: baum_welch, n_iter: 50, tol: 1.0e-4}
`,
  },
  {
    id: "lesson-3-forward-algorithm",
    title: "Forward algorithm",
    estimatedMinutes: 15,
    difficulty: "Beginner",
    description:
      "How do we score a sequence under a model? The forward recursion, animated step-by-step.",
    status: "published",
    content: Lesson3ForwardAlgorithm,
    notebookLink: {
      filename: "07_textbook_aima_umbrella.ipynb",
      title: "AIMA umbrella world — forward & smoothing reproduced",
      description:
        "Reproduces Russell & Norvig Chap. 14 filtering and smoothing values within 5×10⁻³ on the canonical 5-step sequence. See forward in action.",
    },
  },
  {
    id: "lesson-4-viterbi",
    title: "Viterbi: most likely state path",
    estimatedMinutes: 12,
    difficulty: "Beginner",
    description:
      "Tracing the single best path through a trellis. The DP that powers state decoding.",
    status: "published",
    content: Lesson4Viterbi,
    presetTopologyYaml: `name: lesson_4_viterbi_demo
n_states: 3
state_names: [sunny, cloudy, rainy]
emission:
  type: multinomial
  n_symbols: 3
startprob: uniform
init: {strategy: uniform, seed: 42}
fit: {algorithm: baum_welch, n_iter: 30, tol: 1.0e-4}
`,
    notebookLink: {
      filename: "08_textbook_dishonest_casino.ipynb",
      title: "Durbin's dishonest casino — Viterbi accuracy assertion",
      description:
        "Samples 1000 rolls from Durbin et al.'s canonical model and asserts Viterbi accuracy ≥ 70% (above the always-fair baseline). Watch Viterbi recover loaded-die runs.",
    },
  },
  {
    id: "lesson-5-baum-welch",
    title: "Baum-Welch: learning the parameters",
    estimatedMinutes: 18,
    difficulty: "Intermediate",
    description:
      "EM in disguise. How the model bootstraps itself from data alone.",
    status: "published",
    content: Lesson5BaumWelch,
    presetTopologyYaml: `name: lesson_5_baum_welch_demo
n_states: 3
state_names: [low, mid, high]
emission:
  type: gaussian
  covariance_type: full
  n_features: 2
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 100, tol: 1.0e-5}
`,
    notebookLink: {
      filename: "01_quickstart.ipynb",
      title: "Quickstart — see EM converge end-to-end",
      description:
        "The same 3-state Gaussian model the lesson walks through, fit live with Baum-Welch. Inspect log-likelihood convergence, transmat, and Viterbi path.",
    },
  },
  {
    id: "lesson-6-constrained-topologies",
    title: "Constrained topologies (Bakis, left-right)",
    estimatedMinutes: 15,
    difficulty: "Intermediate",
    description:
      "When ergodic is wrong: speech, DNA, lifecycle models that forbid back-transitions.",
    status: "published",
    content: Lesson6ConstrainedTopologies,
    presetTopologyYaml: `name: lesson_6_bakis
n_states: 4
state_names: [s0, s1, s2, s3]
emission:
  type: gaussian
  covariance_type: full
  n_features: 1
allowed_transitions:
  - [s0, s0]
  - [s0, s1]
  - [s1, s1]
  - [s1, s2]
  - [s2, s2]
  - [s2, s3]
  - [s3, s3]
startprob: first_state
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 100, tol: 1.0e-5}
`,
    notebookLink: {
      filename: "01_quickstart.ipynb",
      title: "Quickstart — includes a left-right (Bakis) constrained example",
      description:
        "Section 'Try a left-right constrained topology' shows the same lesson concept : declare allowed_transitions, watch the mask × markers, fit, observe forbidden cells stay exactly 0.",
    },
  },
  {
    id: "lesson-7-nhmm",
    title: "Non-homogeneous HMM (NHMM)",
    estimatedMinutes: 15,
    difficulty: "Advanced",
    description:
      "Time-varying transitions driven by external covariates. The breathing transition matrix.",
    status: "published",
    content: Lesson7Nhmm,
    presetTopologyYaml: `name: lesson_7_nhmm_demo
n_states: 3
state_names: [bear, range, bull]
emission:
  type: gaussian
  covariance_type: full
  n_features: 2
startprob: uniform
init: {strategy: kmeans, seed: 42}
fit: {algorithm: baum_welch, n_iter: 50, tol: 1.0e-4}
`,
    notebookLink: {
      filename: "02_nhmm_crypto.ipynb",
      title: "NHMM for crypto regime detection",
      description:
        "Simulate BTC-like returns with volatility-driven regime switching, fit an NHMM, and inspect A(t) at low-vol vs high-vol timesteps.",
    },
  },
  {
    id: "lesson-8-gmm-hmm",
    title: "GMM-HMM : sub-modes inside each regime",
    estimatedMinutes: 15,
    difficulty: "Advanced",
    description:
      "When a single Gaussian per state isn't enough : Gaussian-mixture emissions, covariate-driven transitions, and when the extra parameters pay for themselves.",
    status: "published",
    content: Lesson8GmmHmm,
    notebookLink: {
      filename: "05_gmm_nhmm_submodes.ipynb",
      title: "GMM-NHMM sub-modes — runnable example",
      description:
        "2 regimes × 2 sub-modes each (calm vs volatile), vol-driven covariate, BIC comparison vs single-Gaussian baseline proving the mixture pays for itself.",
    },
  },
  {
    id: "lesson-9-factorial-nhmm",
    title: "Factorial NHMM : independent regime dimensions",
    estimatedMinutes: 18,
    difficulty: "Advanced",
    description:
      "When the hidden state is a tuple : D parallel chains, K_joint = product of K_d, parameter savings vs the flat joint HMM.",
    status: "published",
    content: Lesson9FactorialNhmm,
    notebookLink: {
      filename: "06_factorial_nhmm_multifactor.ipynb",
      title: "Factorial NHMM multi-factor — trend × vol",
      description:
        "Trend (3 states) × vol (2 states) with per-chain covariates. Computes the parameter savings vs joint HMM and demonstrates decode_chain / A_t per chain.",
    },
  },
  {
    id: "lesson-10-bayesian-hmm",
    title: "Bayesian HMM : credible intervals on parameters",
    estimatedMinutes: 18,
    difficulty: "Advanced",
    description:
      "Posterior distributions instead of point estimates. PyMC NUTS sampler, full arviz InferenceData, when to reach for it vs Baum-Welch.",
    status: "published",
    content: Lesson10BayesianHmm,
    notebookLink: {
      filename: "09_bayesian_hmm.ipynb",
      title: "Bayesian HMM — full posterior with PyMC NUTS",
      description:
        "Runs the BayesianHMMBackend on a 3-state Gaussian model. Shows credible intervals on transmat / means, posterior predictive checks, and arviz convergence diagnostics. Requires `pip install \"hmm-studio[bayesian]\"`.",
    },
  },
  {
    id: "lesson-11-semi-supervised",
    title: "Semi-supervised training : partial labels",
    estimatedMinutes: 15,
    difficulty: "Intermediate",
    description:
      "Some states known, others unlabelled. NaN / -1 sentinel API, E-step clamp, when to use it over pure Baum-Welch.",
    status: "published",
    content: Lesson11SemiSupervised,
  },
  {
    id: "lesson-12-hierarchical-hmm",
    title: "Hierarchical HMM (theory only)",
    estimatedMinutes: 12,
    difficulty: "Advanced",
    description:
      "Multi-scale sequences : a regime inside a regime. Fine-Singer-Tishby 1998. Code gated on external signal — concept lesson only.",
    status: "published",
    content: Lesson12HierarchicalHmm,
  },
];

export function getLessonById(id: string): LessonMeta | undefined {
  return LESSONS.find((l) => l.id === id);
}
