export interface ParamHelpEntry {
  title: string;
  body: string;
  lesson?: { id: string; label: string };
}

// Single source of truth for parameter help copy. Keys are stable param ids
// referenced by <HelpTip paramKey="...">. Concepts shared across surfaces
// (seed, K range, n_mix) reuse one entry.
export const PARAM_HELP: Record<string, ParamHelpEntry> = {
  "topology.name": {
    title: "Model name",
    body: "A label for this topology. Saved in result bundles and summaries; it has no effect on the fit.",
  },
  "emission.type": {
    title: "Emission type",
    body: "The distribution each hidden state emits. Gaussian / GMM for continuous data, Multinomial for discrete symbols, Poisson for counts.",
    lesson: { id: "lesson-1-what-is-an-hmm", label: "What is an HMM?" },
  },
  "emission.n_features": {
    title: "Number of features",
    body: "How many observed columns each emission models (the dimensionality of X). Must match your dataset's feature columns.",
    lesson: { id: "lesson-13-choosing-features", label: "Choosing features" },
  },
  "emission.covariance_type": {
    title: "Covariance type",
    body: "Shape of each Gaussian's covariance. 'full' is most flexible (most parameters); 'diag' assumes uncorrelated features; 'tied' shares one matrix; 'spherical' is a single variance per state.",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "emission.n_mix": {
    title: "Mixture components",
    body: "Number of Gaussians blended per state (GMM). More components capture sub-modes within a regime but add parameters — let BIC decide if they pay off.",
    lesson: { id: "lesson-8-gmm-hmm", label: "GMM-HMM" },
  },
  "emission.n_symbols": {
    title: "Number of symbols",
    body: "Size of the discrete alphabet for Multinomial emissions. Your single integer column must contain values in [0, n_symbols).",
    lesson: { id: "lesson-2-markov-chains", label: "Markov chains" },
  },
  "init.strategy": {
    title: "Initialisation strategy",
    body: "How parameters are seeded before EM. 'kmeans' clusters the data first (usually best for Gaussian); 'uniform'/'random' are simpler; 'data_frequencies' seeds from observed counts. Init matters — EM finds a local optimum.",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "init.seed": {
    title: "Random seed",
    body: "Fixes the RNG so the fit is reproducible. Change it to probe sensitivity to initialisation.",
  },
  "fit.n_iter": {
    title: "Max EM iterations",
    body: "Upper bound on Baum-Welch (EM) iterations. The fit stops earlier if the log-likelihood change drops below tol.",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "fit.tol": {
    title: "Convergence tolerance",
    body: "EM stops when the per-iteration log-likelihood improvement falls below this. Smaller = stricter (more iterations).",
    lesson: { id: "lesson-5-baum-welch", label: "Baum-Welch" },
  },
  "priors.alpha": {
    title: "Dirichlet prior (α)",
    body: "Smoothing on the transition rows. α > 1 pulls toward uniform; α = 1 (or empty) is plain MLE. Useful when some transitions are rarely observed.",
    lesson: { id: "lesson-10-bayesian-hmm", label: "Bayesian HMM" },
  },
  "topology.allowed_transitions": {
    title: "Transition shape",
    body: "Which state-to-state moves are allowed. Ergodic permits all; left-right / Bakis forbid going back — right for staged processes (speech phonemes, lifecycles) where you never revisit a past regime.",
    lesson: { id: "lesson-6-constrained-topologies", label: "Constrained topologies" },
  },
  "scan.k_range": {
    title: "Number of states (K)",
    body: "The hidden-state count to sweep. A scan/compare fits one model per K in [k_min, k_max] and ranks them by information criterion.",
  },
  "compare.emission_types": {
    title: "Emission families to compare",
    body: "Which P(X) families to put in the grid. All are directly comparable by BIC/AIC/HQIC. Each family is fit at every K in the range.",
    lesson: { id: "lesson-8-gmm-hmm", label: "GMM-HMM" },
  },
};
