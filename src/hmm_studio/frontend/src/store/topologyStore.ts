import { create, useStore } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { temporal } from "zundo";
import type { TemporalState } from "zundo";

export type EmissionType = "gaussian" | "gmm" | "multinomial" | "poisson";
export type CovarianceType = "full" | "diag" | "tied" | "spherical";

export interface EmissionSpec {
  type: EmissionType;
  n_features: number | null;
  covariance_type: CovarianceType | null;
  n_mix: number | null;
  n_symbols: number | null;
}

export interface InitSpec {
  strategy: "uniform" | "random" | "kmeans" | "data_frequencies";
  seed: number;
}

export interface FitSpec {
  algorithm: "baum_welch";
  n_iter: number;
  tol: number;
}

export interface StateNode {
  id: string;
  name: string;
  position: { x: number; y: number };
  // B.4.2: per-state init hints (optional). When set, overrides the global init
  // strategy for this state. Shape depends on the global emission.type:
  //   gaussian / gmm  → init_mean: number[] (n_features)
  //   poisson         → init_lambda: number[] (n_features)
  //   multinomial     → init_emissionprob: number[] (n_symbols)
  init_mean?: number[];
  init_lambda?: number[];
  init_emissionprob?: number[];
}

export interface TransitionEdge {
  id: string;
  source: string;
  target: string;
}

export interface TopologyState {
  name: string;
  states: StateNode[];
  transitions: TransitionEdge[];
  emission: EmissionSpec;
  startprob: "uniform" | "first_state" | number[];
  init: InitSpec;
  fit: FitSpec;
  // B.4.2: tracks which state node is currently selected in the canvas
  selectedStateId: string | null;

  setName: (name: string) => void;
  addState: (position: { x: number; y: number }) => void;
  renameState: (id: string, name: string) => void;
  removeState: (id: string) => void;
  moveState: (id: string, position: { x: number; y: number }) => void;
  addTransition: (source: string, target: string) => void;
  removeTransition: (id: string) => void;
  setEmission: (emission: EmissionSpec) => void;
  setStartprob: (sp: "uniform" | "first_state" | number[]) => void;
  setInit: (init: InitSpec) => void;
  setFit: (fit: FitSpec) => void;
  loadTopology: (raw: Partial<Omit<TopologyState, "loadTopology" | "reset" | "setName" | "addState" | "renameState" | "removeState" | "moveState" | "addTransition" | "removeTransition" | "setEmission" | "setStartprob" | "setInit" | "setFit" | "setStateInit" | "setSelectedStateId">>) => void;
  reset: () => void;
  setStateInit: (
    id: string,
    key: "init_mean" | "init_lambda" | "init_emissionprob",
    values: number[] | undefined,
  ) => void;
  setSelectedStateId: (id: string | null) => void;
}

/** The serialisable data slice — everything except action functions. */
export type TopologyData = Pick<
  TopologyState,
  "name" | "states" | "transitions" | "emission" | "startprob" | "init" | "fit"
>;
// Note: selectedStateId is intentionally excluded from TopologyData (not in undo history)

const DEFAULT_STATE = {
  name: "untitled",
  states: [] as StateNode[],
  transitions: [] as TransitionEdge[],
  emission: {
    type: "gaussian" as EmissionType,
    n_features: 1,
    covariance_type: "full" as CovarianceType,
    n_mix: null,
    n_symbols: null,
  } as EmissionSpec,
  startprob: "uniform" as "uniform" | "first_state" | number[],
  init: { strategy: "kmeans" as const, seed: 42 } as InitSpec,
  fit: { algorithm: "baum_welch" as const, n_iter: 200, tol: 1e-4 } as FitSpec,
  selectedStateId: null as string | null,
};

function _uid(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

export const useTopologyStore = create<TopologyState>()(
  persist(
    temporal(
      (set) => ({
        ...DEFAULT_STATE,
        setName: (name) => set({ name }),
        addState: (position) =>
          set((s) => {
            const id = _uid("s");
            const newState: StateNode = {
              id,
              name: `s${s.states.length}`,
              position,
            };
            return { states: [...s.states, newState] };
          }),
        renameState: (id, name) =>
          set((s) => ({
            states: s.states.map((n) => (n.id === id ? { ...n, name } : n)),
          })),
        removeState: (id) =>
          set((s) => ({
            states: s.states.filter((n) => n.id !== id),
            transitions: s.transitions.filter(
              (e) => e.source !== id && e.target !== id,
            ),
          })),
        moveState: (id, position) =>
          set((s) => ({
            states: s.states.map((n) => (n.id === id ? { ...n, position } : n)),
          })),
        addTransition: (source, target) =>
          set((s) => {
            if (s.transitions.some((e) => e.source === source && e.target === target)) {
              return {};
            }
            return {
              transitions: [
                ...s.transitions,
                { id: _uid("e"), source, target },
              ],
            };
          }),
        removeTransition: (id) =>
          set((s) => ({ transitions: s.transitions.filter((e) => e.id !== id) })),
        setEmission: (emission) => set({ emission }),
        setStartprob: (startprob) => set({ startprob }),
        setInit: (init) => set({ init }),
        setFit: (fit) => set({ fit }),
        loadTopology: (raw) => set({ ...DEFAULT_STATE, ...raw }),
        reset: () => set(DEFAULT_STATE),
        setStateInit: (id, key, values) =>
          set((s) => ({
            states: s.states.map((n) =>
              n.id === id ? { ...n, [key]: values } : n,
            ),
          })),
        setSelectedStateId: (id) => set({ selectedStateId: id }),
      }),
      {
        partialize: (state) => {
          const {
            setName,
            addState,
            renameState,
            removeState,
            moveState,
            addTransition,
            removeTransition,
            setEmission,
            setStartprob,
            setInit,
            setFit,
            loadTopology,
            reset,
            setStateInit,
            setSelectedStateId,
            selectedStateId,
            ...data
          } = state;
          return data;
        },
        limit: 50,
      },
    ),
    {
      name: "hmm-studio-topology",
      storage: createJSONStorage(() => localStorage),
      // Only persist the data fields — not action functions, selection, or
      // the temporal middleware's internal undo/redo history.
      partialize: (state) => ({
        name: state.name,
        states: state.states,
        transitions: state.transitions,
        emission: state.emission,
        startprob: state.startprob,
        init: state.init,
        fit: state.fit,
      }),
      version: 1,
    },
  ),
);

// The temporal store tracks only the data slice (actions are excluded by partialize).
// We expose the raw StoreApi so callers can subscribe with useStore from zustand.
export const topologyTemporalStore = useTopologyStore.temporal;

export const useTopologyTemporal = <T,>(
  selector: (state: TemporalState<TopologyData>) => T,
): T => useStore(useTopologyStore.temporal as import("zustand").StoreApi<TemporalState<TopologyData>>, selector);
