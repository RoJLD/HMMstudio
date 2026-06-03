import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { TopologyData } from "./topologyStore";

export interface SavedTopology {
  name: string;
  data: TopologyData;
  savedAt: number;
}

interface SavedTopologiesState {
  saved: Record<string, SavedTopology>;
  save: (entry: SavedTopology) => void;
  remove: (name: string) => void;
  setSaved: (saved: Record<string, SavedTopology>) => void;
}

// Sibling of topologyStore (NOT the active model): a named library of saved
// topologies. Own localStorage key; no undo. This is the A2 stop-gap and the
// exact data shape the future multi-tab (A1) docs-map will reuse.
export const useSavedTopologies = create<SavedTopologiesState>()(
  persist(
    (set) => ({
      saved: {},
      save: (entry) =>
        set((s) => ({ saved: { ...s.saved, [entry.name]: entry } })),
      remove: (name) =>
        set((s) => {
          const next = { ...s.saved };
          delete next[name];
          return { saved: next };
        }),
      setSaved: (saved) => set({ saved }),
    }),
    {
      name: "hmm-studio-saved-topologies",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
