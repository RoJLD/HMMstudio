import yaml from "js-yaml";
import type {
  CovarianceType,
  EmissionType,
  TopologyData,
  TopologyState,
} from "../store/topologyStore";

interface TopologyEmissionYAML {
  type?: string;
  n_features?: number | null;
  covariance_type?: string | null;
  n_mix?: number | null;
  n_symbols?: number | null;
  // B.4.2: per-state init hints
  init_mean?: number[];
  init_lambda?: number[];
  init_emissionprob?: number[];
}

interface TopologyYAML {
  name?: string;
  n_states?: number;
  state_names?: string[];
  emission?: TopologyEmissionYAML;
  // B.4.2: per-state emissions list (one entry per state, index-aligned)
  emissions?: TopologyEmissionYAML[];
  allowed_transitions?: string[][];
  startprob?: string | number[];
  init?: { strategy?: string; seed?: number };
  fit?: { algorithm?: string; n_iter?: number; tol?: number };
  // B.4.3 / A.9: transmat Dirichlet priors
  transmat_prior_alpha?: number;
  transmat_prior_matrix?: number[][];
}

type TopologyPartial = Parameters<TopologyState["loadTopology"]>[0];

export function topologyToYAML(state: TopologyData): string {
  const emissionObj: Record<string, unknown> = { type: state.emission.type };
  if (state.emission.n_features !== null) emissionObj.n_features = state.emission.n_features;
  if (state.emission.covariance_type !== null) emissionObj.covariance_type = state.emission.covariance_type;
  if (state.emission.n_mix !== null) emissionObj.n_mix = state.emission.n_mix;
  if (state.emission.n_symbols !== null) emissionObj.n_symbols = state.emission.n_symbols;

  const obj: Record<string, unknown> = {
    name: state.name,
    n_states: state.states.length,
    state_names: state.states.map((s) => s.name),
    emission: emissionObj,
    startprob: state.startprob,
    init: state.init,
    fit: state.fit,
  };

  if (state.transitions.length > 0) {
    obj.allowed_transitions = state.transitions.map((t) => {
      const srcName = state.states.find((s) => s.id === t.source)?.name ?? t.source;
      const tgtName = state.states.find((s) => s.id === t.target)?.name ?? t.target;
      return [srcName, tgtName];
    });
  }

  // B.4.2: emit per-state emissions list when any state has init hints
  const anyPerState = state.states.some(
    (s) => s.init_mean || s.init_lambda || s.init_emissionprob,
  );
  if (anyPerState) {
    obj.emissions = state.states.map((s) => {
      const e: Record<string, unknown> = {
        type: state.emission.type,
      };
      if (state.emission.n_features !== null)
        e.n_features = state.emission.n_features;
      if (state.emission.covariance_type !== null)
        e.covariance_type = state.emission.covariance_type;
      if (state.emission.n_mix !== null) e.n_mix = state.emission.n_mix;
      if (state.emission.n_symbols !== null)
        e.n_symbols = state.emission.n_symbols;
      if (s.init_mean !== undefined) e.init_mean = s.init_mean;
      if (s.init_lambda !== undefined) e.init_lambda = s.init_lambda;
      if (s.init_emissionprob !== undefined)
        e.init_emissionprob = s.init_emissionprob;
      return e;
    });
  }

  // B.4.3 / A.9: serialize transmat priors
  if (state.transmat_prior_alpha !== null) {
    obj.transmat_prior_alpha = state.transmat_prior_alpha;
  }

  // Per-edge overrides → build a K×K matrix
  const anyEdgeOverride = state.transitions.some(
    (t) => t.prior_weight !== undefined,
  );
  if (anyEdgeOverride) {
    const K = state.states.length;
    const baseAlpha = state.transmat_prior_alpha ?? 1.0;
    const stateIdToIdx = new Map(state.states.map((s, i) => [s.id, i]));
    // Initialize matrix: 0 on forbidden edges (no transition), baseAlpha on allowed
    const matrix: number[][] = Array.from({ length: K }, () => Array(K).fill(0));
    state.transitions.forEach((t) => {
      const i = stateIdToIdx.get(t.source);
      const j = stateIdToIdx.get(t.target);
      if (i === undefined || j === undefined) return;
      matrix[i][j] = t.prior_weight ?? baseAlpha;
    });
    obj.transmat_prior_matrix = matrix;
  }

  return yaml.dump(obj, { lineWidth: 100 });
}

export function yamlToTopology(text: string): TopologyPartial {
  const obj = yaml.load(text) as TopologyYAML;
  if (!obj || typeof obj !== "object") {
    throw new Error("YAML did not parse to an object");
  }

  const names = obj.state_names ?? [];
  const states: import("../store/topologyStore").StateNode[] = names.map((name, i) => ({
    id: `s-${i}-${Math.random().toString(36).slice(2, 6)}`,
    name,
    position: { x: 60 + (i % 4) * 240, y: 60 + Math.floor(i / 4) * 160 },
  }));

  // B.4.2: parse per-state emissions if present and length matches
  if (Array.isArray(obj.emissions) && obj.emissions.length === states.length) {
    obj.emissions.forEach((e: TopologyEmissionYAML, i: number) => {
      if (e?.init_mean) states[i].init_mean = e.init_mean;
      if (e?.init_lambda) states[i].init_lambda = e.init_lambda;
      if (e?.init_emissionprob) states[i].init_emissionprob = e.init_emissionprob;
    });
  }

  const nameToId = new Map(states.map((s) => [s.name, s.id]));
  const transitions = (obj.allowed_transitions ?? []).map((pair, i) => ({
    id: `e-${i}-${Math.random().toString(36).slice(2, 6)}`,
    source: nameToId.get(pair[0]) ?? pair[0],
    target: nameToId.get(pair[1]) ?? pair[1],
  }));

  // B.4.3 / A.9: parse transmat priors
  const transmat_prior_alpha =
    typeof obj.transmat_prior_alpha === "number"
      ? obj.transmat_prior_alpha
      : null;

  // If a matrix is present, distribute the per-edge overrides back onto
  // the transitions list (matching by (src,tgt) name pair via state_names).
  if (Array.isArray(obj.transmat_prior_matrix) && transitions.length > 0) {
    const matrix = obj.transmat_prior_matrix;
    // We need to map matrix[i][j] back to a transition by index — use
    // the state_names order (i = index of source name).
    const nameToIdx = new Map(
      (obj.state_names ?? []).map((n, i) => [n, i]),
    );
    transitions.forEach((t) => {
      const srcName = states.find((s) => s.id === t.source)?.name;
      const tgtName = states.find((s) => s.id === t.target)?.name;
      if (srcName === undefined || tgtName === undefined) return;
      const i = nameToIdx.get(srcName);
      const j = nameToIdx.get(tgtName);
      if (i === undefined || j === undefined) return;
      const w = matrix[i]?.[j];
      if (
        typeof w === "number" &&
        transmat_prior_alpha !== null &&
        w !== transmat_prior_alpha
      ) {
        (t as import("../store/topologyStore").TransitionEdge).prior_weight = w;
      } else if (
        typeof w === "number" &&
        transmat_prior_alpha === null &&
        w !== 1.0  // default alpha = 1 = MLE
      ) {
        (t as import("../store/topologyStore").TransitionEdge).prior_weight = w;
      }
    });
  }

  return {
    name: obj.name ?? "untitled",
    states,
    transitions,
    emission: {
      type: (obj.emission?.type ?? "gaussian") as EmissionType,
      n_features: obj.emission?.n_features ?? null,
      covariance_type:
        (obj.emission?.covariance_type ?? null) as CovarianceType | null,
      n_mix: obj.emission?.n_mix ?? null,
      n_symbols: obj.emission?.n_symbols ?? null,
    },
    startprob: typeof obj.startprob === "string"
      ? (obj.startprob as "uniform" | "first_state")
      : (obj.startprob ?? "uniform"),
    init: {
      strategy: (obj.init?.strategy ?? "kmeans") as TopologyState["init"]["strategy"],
      seed: obj.init?.seed ?? 42,
    },
    fit: {
      algorithm: "baum_welch",
      n_iter: obj.fit?.n_iter ?? 200,
      tol: obj.fit?.tol ?? 1e-4,
    },
    transmat_prior_alpha,  // B.4.3
  };
}
