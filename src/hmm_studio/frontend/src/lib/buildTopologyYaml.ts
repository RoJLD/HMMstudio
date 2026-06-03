import yaml from "js-yaml";
import type { DatasetPreview } from "../api/client";

export type WizardEmissionType = "gaussian" | "gmm" | "multinomial" | "poisson";
export type TransitionShape = "ergodic" | "left-right" | "bakis";

export interface WizardModel {
  name: string;
  emissionType: WizardEmissionType;
  nFeatures: number; // gaussian/gmm/poisson
  covarianceType: "full" | "diag" | "tied" | "spherical"; // gaussian/gmm
  nMix: number; // gmm
  nSymbols: number; // multinomial
  k: number;
  stateNames: string[]; // length k
  shape: TransitionShape;
  initStrategy: "uniform" | "random" | "kmeans" | "data_frequencies";
  seed: number;
  nIter: number;
  tol: number;
  priorAlpha: number | null;
}

export interface EmissionSuggestion {
  type: WizardEmissionType;
  nFeatures: number;
  nSymbols: number;
}

const isIntDtype = (dt: string | undefined): boolean => !!dt && /^u?int/i.test(dt);

/** Best-effort emission suggestion from a dataset preview. Always overridable. */
export function suggestEmission(preview: DatasetPreview | null | undefined): EmissionSuggestion {
  if (!preview || preview.columns.length === 0) {
    return { type: "gaussian", nFeatures: 1, nSymbols: 2 };
  }
  const cols = preview.columns;
  const colValues = (c: string): number[] =>
    preview.head.map((row) => row[c]).filter((v): v is number => typeof v === "number");

  if (cols.length === 1 && isIntDtype(preview.dtypes[cols[0]])) {
    const vals = colValues(cols[0]);
    const maxV = vals.length ? Math.max(...vals) : 1;
    return { type: "multinomial", nFeatures: 1, nSymbols: Math.max(2, maxV + 1) };
  }
  const allInt = cols.every((c) => isIntDtype(preview.dtypes[c]));
  if (allInt && cols.every((c) => colValues(c).every((v) => v >= 0))) {
    return { type: "poisson", nFeatures: cols.length, nSymbols: 2 };
  }
  return { type: "gaussian", nFeatures: cols.length, nSymbols: 2 };
}

/** allowed_transitions name-pairs for a shape. */
export function allowedTransitionsForShape(shape: TransitionShape, names: string[]): string[][] {
  if (shape === "ergodic") {
    // Materialize the full mesh (incl. self-loops) so ergodic models show
    // editable arrows instead of zero. Semantically identical to an omitted
    // mask (all transitions allowed), but now visible + per-edge-prior-able.
    const pairs: string[][] = [];
    for (const a of names) for (const b of names) pairs.push([a, b]);
    return pairs;
  }
  const pairs: string[][] = [];
  const K = names.length;
  for (let i = 0; i < K; i++) {
    pairs.push([names[i], names[i]]); // self-loop
    if (i + 1 < K) pairs.push([names[i], names[i + 1]]); // forward
    if (shape === "bakis" && i + 2 < K) pairs.push([names[i], names[i + 2]]); // skip-one
  }
  return pairs;
}

/** Assemble a standard topology YAML string from the wizard model (pure). */
export function buildTopologyYaml(m: WizardModel): string {
  const emission: Record<string, unknown> = { type: m.emissionType };
  if (m.emissionType === "gaussian" || m.emissionType === "gmm" || m.emissionType === "poisson") {
    emission.n_features = m.nFeatures;
  }
  if (m.emissionType === "gaussian" || m.emissionType === "gmm") {
    emission.covariance_type = m.covarianceType;
  }
  if (m.emissionType === "gmm") emission.n_mix = m.nMix;
  if (m.emissionType === "multinomial") emission.n_symbols = m.nSymbols;

  const obj: Record<string, unknown> = {
    name: m.name || "untitled",
    n_states: m.k,
    state_names: m.stateNames,
    emission,
    startprob: "uniform",
    init: { strategy: m.initStrategy, seed: m.seed },
    fit: { algorithm: "baum_welch", n_iter: m.nIter, tol: m.tol },
  };
  const at = allowedTransitionsForShape(m.shape, m.stateNames);
  if (at.length > 0) obj.allowed_transitions = at;
  if (m.priorAlpha !== null) obj.transmat_prior_alpha = m.priorAlpha;

  return yaml.dump(obj, { lineWidth: 100 });
}
