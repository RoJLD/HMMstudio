import { create } from "zustand";
import type { DatasetPreview } from "../api/client";

interface DatasetStoreState {
  current: DatasetPreview | null;
  history: DatasetPreview[];
  setCurrent: (ds: DatasetPreview | null) => void;
  addToHistory: (ds: DatasetPreview) => void;
}

export const useDatasetStore = create<DatasetStoreState>((set) => ({
  current: null,
  history: [],
  setCurrent: (ds) => set({ current: ds }),
  addToHistory: (ds) =>
    set((s) => ({
      history: [ds, ...s.history.filter((h) => h.id !== ds.id)].slice(0, 10),
    })),
}));
