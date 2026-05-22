import yaml from "js-yaml";
import type {
  CovarianceType,
  EmissionType,
  TopologyState,
} from "../store/topologyStore";

interface TopologyYAML {
  name?: string;
  n_states?: number;
  state_names?: string[];
  emission?: {
    type?: string;
    n_features?: number | null;
    covariance_type?: string | null;
    n_mix?: number | null;
    n_symbols?: number | null;
  };
  allowed_transitions?: string[][];
  startprob?: string | number[];
  init?: { strategy?: string; seed?: number };
  fit?: { algorithm?: string; n_iter?: number; tol?: number };
}

type TopologyPartial = Parameters<TopologyState["loadTopology"]>[0];

export function topologyToYAML(state: TopologyState): string {
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

  return yaml.dump(obj, { lineWidth: 100 });
}

export function yamlToTopology(text: string): TopologyPartial {
  const obj = yaml.load(text) as TopologyYAML;
  if (!obj || typeof obj !== "object") {
    throw new Error("YAML did not parse to an object");
  }

  const names = obj.state_names ?? [];
  const states = names.map((name, i) => ({
    id: `s-${i}-${Math.random().toString(36).slice(2, 6)}`,
    name,
    position: { x: 80 + (i % 4) * 180, y: 80 + Math.floor(i / 4) * 140 },
  }));
  const nameToId = new Map(states.map((s) => [s.name, s.id]));
  const transitions = (obj.allowed_transitions ?? []).map((pair, i) => ({
    id: `e-${i}-${Math.random().toString(36).slice(2, 6)}`,
    source: nameToId.get(pair[0]) ?? pair[0],
    target: nameToId.get(pair[1]) ?? pair[1],
  }));

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
  };
}
