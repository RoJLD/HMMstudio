import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// UI-only editor preferences. Deliberately SEPARATE from topologyStore so that
// toggling them is NOT undoable (zundo) and does NOT enter the topology's
// persisted/serialised model. Persisted under its own localStorage key.
interface EditorPrefs {
  showPriorPreview: boolean;
  setShowPriorPreview: (v: boolean) => void;
}

export const useEditorPrefs = create<EditorPrefs>()(
  persist(
    (set) => ({
      showPriorPreview: false,
      setShowPriorPreview: (v) => set({ showPriorPreview: v }),
    }),
    {
      name: "hmm-studio-editor-prefs",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
