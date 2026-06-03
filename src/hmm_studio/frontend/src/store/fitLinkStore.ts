import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// Links the editor to its most recent fit WITHOUT polluting the pure topology
// model: a UI/side store (own localStorage key, no undo, not in topologyStore).
// lot G reads this to overlay learned probabilities; the fingerprint lets it
// detect a topology that changed since the fit and refuse stale numbers.
interface FitLinkState {
  lastFitJobId: string | null;
  fitFingerprint: string | null;
  setFitLink: (jobId: string, fingerprint: string) => void;
  clearFitLink: () => void;
}

export const useFitLink = create<FitLinkState>()(
  persist(
    (set) => ({
      lastFitJobId: null,
      fitFingerprint: null,
      setFitLink: (jobId, fingerprint) =>
        set({ lastFitJobId: jobId, fitFingerprint: fingerprint }),
      clearFitLink: () => set({ lastFitJobId: null, fitFingerprint: null }),
    }),
    {
      name: "hmm-studio-fit-link",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
