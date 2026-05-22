import type { ReactNode } from "react";
import { Lesson1WhatIsAnHmm } from "./lesson-1-what-is-an-hmm";
import { Lesson2MarkovChains } from "./lesson-2-markov-chains";
import { Lesson3ForwardAlgorithm } from "./lesson-3-forward-algorithm";
import { Lesson4Viterbi } from "./lesson-4-viterbi";
import { Lesson5BaumWelch } from "./lesson-5-baum-welch";
import { Lesson6ConstrainedTopologies } from "./lesson-6-constrained-topologies";
import { Lesson7Nhmm } from "./lesson-7-nhmm";

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
  },
];

export function getLessonById(id: string): LessonMeta | undefined {
  return LESSONS.find((l) => l.id === id);
}
