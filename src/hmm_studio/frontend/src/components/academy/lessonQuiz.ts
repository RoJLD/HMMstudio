// Quiz + flashcard content for Academy lessons. Pure data, keyed by lesson id —
// like paramHelp, adding content = editing this file, no logic changes.
// Each question carries a cognitive level (Recall/Apply/Analyze) used by the
// gap report, plus a short `concept` tag and an `explanation` shown after grading.

export type CogLevel = "Recall" | "Apply" | "Analyze";

export interface Flashcard {
  front: string;
  back: string;
  level: CogLevel;
}

export interface QuizQuestion {
  prompt: string;
  options: string[];
  correct: number; // index into options
  level: CogLevel;
  explanation: string;
  concept: string;
}

export interface LessonQuiz {
  flashcards: Flashcard[];
  questions: QuizQuestion[];
}

export const LESSON_QUIZZES: Record<string, LessonQuiz> = {
  "lesson-1-what-is-an-hmm": {
    flashcards: [
      { level: "Recall", front: "What are the two layers in an HMM?", back: "A hidden state sequence (a Markov chain) and an observed emission produced at each step." },
      { level: "Recall", front: "What does “hidden” mean in HMM?", back: "The state is never observed directly — only the emissions it generates are seen." },
      { level: "Apply", front: "You see daily returns and want to label market regimes. Which layer is the regime?", back: "The hidden state — regimes are latent; the returns are the emissions." },
    ],
    questions: [
      { level: "Recall", prompt: "In an HMM, what is directly observed?", options: ["The hidden states", "The emissions / observations", "The transition matrix", "The number of states"], correct: 1, concept: "hidden vs observed", explanation: "Only emissions are observed; the states are inferred from them." },
      { level: "Apply", prompt: "A 3-state HMM models temperature readings. The 3 states represent…", options: ["3 sensors", "3 latent regimes (e.g. cold/mild/hot)", "3 time steps", "3 features"], correct: 1, concept: "states as regimes", explanation: "States are latent regimes that generate the readings." },
      { level: "Analyze", prompt: "Why use an HMM instead of clustering each observation independently?", options: ["It is faster", "It models temporal dependence between successive states", "It needs no parameters", "It avoids emissions"], correct: 1, concept: "temporal dependence", explanation: "The Markov chain links consecutive labels; plain clustering ignores order." },
    ],
  },
  "lesson-2-markov-chains": {
    flashcards: [
      { level: "Recall", front: "State the Markov property.", back: "The next state depends only on the current state, not on the full history." },
      { level: "Recall", front: "What must each row of a transition matrix sum to?", back: "1 — each row is a probability distribution over the next state." },
      { level: "Apply", front: "For 3 states, each transition-matrix row lives on what geometric object?", back: "A 2-simplex (a triangle): three next-state probabilities summing to 1." },
    ],
    questions: [
      { level: "Recall", prompt: "A transition matrix for K states has shape…", options: ["K×1", "K×K", "1×K", "K×T"], correct: 1, concept: "transmat shape", explanation: "One row per current state, one column per next state." },
      { level: "Apply", prompt: "Row i of the transition matrix gives…", options: ["P(observation | state i)", "P(next state | current state i)", "the stationary distribution", "the emission means"], correct: 1, concept: "transmat rows", explanation: "Row i is the distribution over the next state given you are in state i." },
      { level: "Analyze", prompt: "A row equal to [0.9, 0.1, 0.0] means that state is…", options: ["equally likely to go anywhere", "very persistent (likely to stay)", "guaranteed to switch", "invalid"], correct: 1, concept: "persistence", explanation: "A large self-transition makes the regime sticky/persistent." },
    ],
  },
  "lesson-3-forward-algorithm": {
    flashcards: [
      { level: "Recall", front: "What does the forward algorithm compute?", back: "The likelihood P(observations | model), via summed partial probabilities α." },
      { level: "Analyze", front: "What does αₜ(i) represent?", back: "P(observations up to time t AND being in state i at t)." },
      { level: "Apply", front: "Why not just enumerate every state path?", back: "There are K^T paths (exponential); the forward recursion is only O(T·K²)." },
    ],
    questions: [
      { level: "Recall", prompt: "The forward algorithm gives…", options: ["the single best path", "the data likelihood under the model", "the parameters", "the number of states"], correct: 1, concept: "forward = likelihood", explanation: "Forward sums over all paths to score the sequence." },
      { level: "Apply", prompt: "Forward-algorithm complexity for T steps and K states?", options: ["O(T)", "O(K^T)", "O(T·K²)", "O(T²)"], correct: 2, concept: "complexity", explanation: "Dynamic programming over the trellis: O(T·K²)." },
      { level: "Analyze", prompt: "Forward sums over paths; Viterbi instead…", options: ["also sums", "takes the max (one best path)", "ignores transitions", "is random"], correct: 1, concept: "sum vs max", explanation: "Same recursion shape, but Viterbi maximizes rather than sums." },
    ],
  },
  "lesson-4-viterbi": {
    flashcards: [
      { level: "Recall", front: "What does Viterbi return?", back: "The single most likely hidden state sequence given the observations." },
      { level: "Apply", front: "Viterbi replaces the forward algorithm's sum with what?", back: "A maximum (and stores argmax back-pointers)." },
      { level: "Analyze", front: "Why is backtracking needed in Viterbi?", back: "You store argmax pointers forward, then trace back from the best final state to recover the path." },
    ],
    questions: [
      { level: "Recall", prompt: "Viterbi decoding finds…", options: ["the likelihood", "the most probable state path", "the emission means", "the prior"], correct: 1, concept: "viterbi output", explanation: "It is the MAP path over the whole sequence." },
      { level: "Apply", prompt: "Viterbi differs from forward by replacing the sum with…", options: ["a product", "a maximum", "a logarithm", "a derivative"], correct: 1, concept: "max vs sum", explanation: "Max over predecessors instead of summation." },
      { level: "Analyze", prompt: "Per-timestep posterior decoding can differ from Viterbi because it…", options: ["is simply wrong", "maximizes each marginal, not the joint path", "ignores the data", "is identical"], correct: 1, concept: "viterbi vs posterior", explanation: "Greedy per-state maxima need not form the globally optimal path." },
    ],
  },
  "lesson-5-baum-welch": {
    flashcards: [
      { level: "Recall", front: "Baum-Welch is an instance of which general algorithm?", back: "Expectation-Maximization (EM)." },
      { level: "Apply", front: "What does the E-step compute?", back: "Posterior state and transition responsibilities (γ, ξ) via forward-backward." },
      { level: "Analyze", front: "Why can Baum-Welch get “stuck”?", back: "EM converges only to a local optimum of the likelihood — initialization matters." },
    ],
    questions: [
      { level: "Recall", prompt: "Baum-Welch trains an HMM using…", options: ["labeled state sequences", "EM on unlabeled sequences", "linear regression", "Viterbi alone"], correct: 1, concept: "BW = EM", explanation: "It learns parameters from observations without state labels." },
      { level: "Apply", prompt: "The M-step uses the E-step responsibilities to…", options: ["do nothing", "re-estimate transition & emission parameters", "decode the path", "compute BIC"], correct: 1, concept: "M-step", explanation: "It updates parameters to maximize the expected complete-data likelihood." },
      { level: "Analyze", prompt: "Across Baum-Welch iterations the data log-likelihood should…", options: ["decrease", "be non-decreasing up to convergence", "oscillate randomly", "stay constant"], correct: 1, concept: "monotone LL", explanation: "EM guarantees the log-likelihood never decreases between iterations." },
    ],
  },
  "lesson-6-constrained-topologies": {
    flashcards: [
      { level: "Recall", front: "What is a left-right (Bakis) topology?", back: "States can only stay or advance; back-transitions are forbidden." },
      { level: "Apply", front: "Where are left-right HMMs natural?", back: "Speech phonemes, lifecycles, degradation — processes that never revisit a past stage." },
      { level: "Analyze", front: "How is a forbidden transition enforced during EM?", back: "Its probability is masked to exactly 0 at every M-step." },
    ],
    questions: [
      { level: "Recall", prompt: "An ergodic topology allows…", options: ["only forward moves", "every state to follow every state", "no self-loops", "only one state"], correct: 1, concept: "ergodic", explanation: "Ergodic = fully connected transitions." },
      { level: "Apply", prompt: "Modeling a machine that breaks and never self-repairs suggests…", options: ["ergodic", "left-right / no back-transition", "a single state", "multinomial emissions"], correct: 1, concept: "left-right use", explanation: "The process cannot return to a healthier state." },
      { level: "Analyze", prompt: "A masked transition stays exactly 0 after fitting because…", options: ["luck", "the mask is re-applied every M-step", "emissions forbid it", "of the prior"], correct: 1, concept: "mask enforcement", explanation: "The constraint is enforced at each iteration, not just at init." },
    ],
  },
  "lesson-7-nhmm": {
    flashcards: [
      { level: "Recall", front: "What does “non-homogeneous” mean in NHMM?", back: "The transition matrix changes over time, driven by external covariates." },
      { level: "Apply", front: "Give a crypto example of an NHMM covariate.", back: "Volatility driving the regime-switching probabilities A(t)." },
      { level: "Analyze", front: "Plain HMM vs NHMM transitions?", back: "Plain HMM has a fixed A; NHMM has A(t) = f(covariates at t)." },
    ],
    questions: [
      { level: "Recall", prompt: "An NHMM makes which component time-varying?", options: ["the emissions", "the transition matrix", "the number of states", "the data"], correct: 1, concept: "A(t)", explanation: "Transitions become a function of covariates over time." },
      { level: "Apply", prompt: "An NHMM models P(X | Z). Is its log-likelihood directly BIC-comparable to a plain HMM's?", options: ["yes, always", "no — it is conditioned on covariates", "only if K matches", "BIC never applies"], correct: 1, concept: "comparability", explanation: "Conditional likelihood is not on the same scale as P(X)." },
      { level: "Analyze", prompt: "Adding a covariate to transitions is worthwhile when…", options: ["always", "it actually shifts switching probabilities enough to beat the parameter penalty", "never", "K is large"], correct: 1, concept: "covariate value", explanation: "Extra parameters must earn their keep on the criterion." },
    ],
  },
  "lesson-8-gmm-hmm": {
    flashcards: [
      { level: "Recall", front: "What does a GMM-HMM change vs a Gaussian HMM?", back: "Each state emits a mixture of Gaussians instead of a single one." },
      { level: "Apply", front: "When do you need GMM emissions?", back: "When one regime has several sub-modes (a multi-modal emission distribution)." },
      { level: "Analyze", front: "What is the cost of more mixture components?", back: "More parameters — use BIC to judge whether the richer emission pays off." },
    ],
    questions: [
      { level: "Recall", prompt: "n_mix in a GMM-HMM is…", options: ["the number of states", "the number of Gaussians per state", "the number of features", "the iteration count"], correct: 1, concept: "n_mix", explanation: "Mixtures per state, not states." },
      { level: "Apply", prompt: "A state's emission histogram is clearly bimodal. A single Gaussian will…", options: ["fit it perfectly", "underfit (miss the two modes)", "overfit", "be exact"], correct: 1, concept: "multimodal", explanation: "One Gaussian cannot represent two modes." },
      { level: "Analyze", prompt: "Going 1→3 mixtures raises log-lik but worsens BIC. You should…", options: ["use 3 anyway", "prefer fewer — the extra mixtures don't justify their parameters", "ignore BIC", "add even more"], correct: 1, concept: "BIC tradeoff", explanation: "BIC penalizes the added parameters more than the fit gain." },
    ],
  },
  "lesson-9-factorial-nhmm": {
    flashcards: [
      { level: "Recall", front: "What is the hidden state in a factorial HMM?", back: "A tuple over D parallel chains — a factored state." },
      { level: "Apply", front: "Why factor the state instead of one flat chain?", back: "The joint size K_joint = ∏K_d explodes; factoring keeps the parameter count tractable." },
      { level: "Analyze", front: "Trend(3)×Vol(2) factorial vs flat joint — the win?", back: "Two small chains instead of a 6-state flat chain with a full 6×6 transition matrix." },
    ],
    questions: [
      { level: "Recall", prompt: "A factorial HMM's hidden state is…", options: ["a single integer", "a tuple over D chains", "an emission", "a covariate"], correct: 1, concept: "factored state", explanation: "Several chains evolve in parallel." },
      { level: "Apply", prompt: "D=3 chains of K=3 — the flat joint has how many states?", options: ["9", "27", "3", "6"], correct: 1, concept: "K_joint", explanation: "3³ = 27 joint states — exactly why factoring helps." },
      { level: "Analyze", prompt: "Factoring assumes the chains are…", options: ["identical", "evolving in parallel with separate transitions", "a single chain", "directly observed"], correct: 1, concept: "parallel chains", explanation: "Each chain has its own dynamics." },
    ],
  },
  "lesson-10-bayesian-hmm": {
    flashcards: [
      { level: "Recall", front: "What does a Bayesian HMM give beyond point estimates?", back: "Posterior distributions (credible intervals) over the parameters." },
      { level: "Apply", front: "Which sampler does the PyMC backend use?", back: "NUTS (No-U-Turn Sampler), an HMC variant." },
      { level: "Analyze", front: "When prefer Bayesian over Baum-Welch?", back: "When you need uncertainty quantification or priors and can afford sampling time." },
    ],
    questions: [
      { level: "Recall", prompt: "A Bayesian HMM produces…", options: ["a single best transmat", "posterior distributions over parameters", "only the Viterbi path", "no parameters"], correct: 1, concept: "posterior", explanation: "You get a distribution, not just a point estimate." },
      { level: "Apply", prompt: "A credible interval on a transition probability tells you…", options: ["its exact value", "the plausible range given data + prior", "the likelihood", "the decoded path"], correct: 1, concept: "credible interval", explanation: "It quantifies parameter uncertainty." },
      { level: "Analyze", prompt: "The main practical cost of the Bayesian approach is…", options: ["none", "sampling can be slow (minutes+) vs EM", "it can't use priors", "it lacks uncertainty"], correct: 1, concept: "sampling cost", explanation: "MCMC is heavier than EM." },
    ],
  },
  "lesson-11-semi-supervised": {
    flashcards: [
      { level: "Recall", front: "What is semi-supervised HMM training?", back: "Some state labels are known and others unknown; both inform the fit." },
      { level: "Apply", front: "How are known labels injected in the E-step?", back: "The posterior is clamped to the known state at the labeled timesteps." },
      { level: "Analyze", front: "Why bother with partial labels?", back: "They anchor states to meaning and reduce label-switching / bad local optima." },
    ],
    questions: [
      { level: "Recall", prompt: "Semi-supervised training uses…", options: ["all labels", "no labels", "partial labels (some known)", "only emissions"], correct: 2, concept: "partial labels", explanation: "A mix of labeled and unlabeled timesteps." },
      { level: "Apply", prompt: "At a labeled timestep, the E-step posterior is…", options: ["ignored", "clamped to the known state", "randomized", "averaged"], correct: 1, concept: "E-step clamp", explanation: "Known labels fix the responsibility at that step." },
      { level: "Analyze", prompt: "Partial labels help mainly by…", options: ["speeding up I/O", "grounding states to meaning and avoiding bad local optima", "removing emissions", "increasing K"], correct: 1, concept: "anchoring", explanation: "They give EM a meaningful anchor." },
    ],
  },
  "lesson-12-hierarchical-hmm": {
    flashcards: [
      { level: "Recall", front: "What is a hierarchical HMM (HHMM)?", back: "An HMM whose states can themselves be sub-HMMs — multi-scale structure." },
      { level: "Apply", front: "Give a multi-scale example.", back: "A macro-regime (coarse) containing intraday sub-behaviors (fine)." },
      { level: "Analyze", front: "Why does hmm-studio keep HHMM theory-only?", back: "The code is gated on external signal; the concept is taught without a fitted implementation yet." },
    ],
    questions: [
      { level: "Recall", prompt: "A hierarchical HMM models structure that is…", options: ["flat", "multi-scale (states within states)", "unordered", "continuous"], correct: 1, concept: "multi-scale", explanation: "Nested states across scales." },
      { level: "Apply", prompt: "An HHMM suits data with…", options: ["a single regime", "nested regimes at different timescales", "no transitions", "one feature"], correct: 1, concept: "nested regimes", explanation: "Coarse regimes containing finer ones." },
      { level: "Analyze", prompt: "A Fine-Singer-Tishby (1998) HHMM can be expressed as…", options: ["a linear model", "an equivalent (large) flat HMM", "a transformer", "a single GMM"], correct: 1, concept: "flattening", explanation: "It unrolls to a flat HMM, at the cost of many states." },
    ],
  },
  "lesson-13-choosing-features": {
    flashcards: [
      { level: "Recall", front: "What problem does unsupervised feature selection solve?", back: "Too many correlated candidate indicators — pick a decorrelated representative set." },
      { level: "Apply", front: "How are features grouped here?", back: "By mutual information (NMI), then hierarchical clustering; keep one medoid per cluster." },
      { level: "Analyze", front: "Why mutual information rather than linear correlation?", back: "MI captures nonlinear dependence, not just linear association." },
    ],
    questions: [
      { level: "Recall", prompt: "Unsupervised feature selection here clusters features by…", options: ["price", "mutual information", "alphabetical order", "BIC"], correct: 1, concept: "MI clustering", explanation: "Normalized mutual information measures dependence." },
      { level: "Apply", prompt: "From a cluster of 5 redundant indicators you keep…", options: ["all 5", "one representative (the medoid)", "none", "the noisiest one"], correct: 1, concept: "medoid", explanation: "One per cluster decorrelates the set." },
      { level: "Analyze", prompt: "MI is preferred over Pearson correlation because it…", options: ["is faster", "captures nonlinear dependence", "needs no data", "ignores noise"], correct: 1, concept: "nonlinear dependence", explanation: "Pearson only sees linear relationships." },
    ],
  },
};

export function getLessonQuiz(lessonId: string): LessonQuiz | undefined {
  return LESSON_QUIZZES[lessonId];
}
