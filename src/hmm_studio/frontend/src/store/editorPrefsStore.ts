import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type OverlayMode = "none" | "prior" | "learned";

// UI-only editor preferences. SEPARATE from topologyStore so toggling them is
// not undoable and does not enter the serialised model.
interface EditorPrefs {
  overlayMode: OverlayMode;
  setOverlayMode: (m: OverlayMode) => void;
}

/** Persist migration: v0 stored a boolean `showPriorPreview`; v1 stores
 *  `overlayMode`. Pure + exported for testing. */
export function migrateEditorPrefs(
  persisted: unknown,
  version: number,
): { overlayMode: OverlayMode } {
  if (version < 1 && persisted && typeof (persisted as { showPriorPreview?: unknown }).showPriorPreview === "boolean") {
    return { overlayMode: (persisted as { showPriorPreview: boolean }).showPriorPreview ? "prior" : "none" };
  }
  const m = (persisted as { overlayMode?: OverlayMode } | null)?.overlayMode;
  return { overlayMode: m ?? "none" };
}

export const useEditorPrefs = create<EditorPrefs>()(
  persist(
    (set) => ({
      overlayMode: "none",
      setOverlayMode: (m) => set({ overlayMode: m }),
    }),
    {
      name: "hmm-studio-editor-prefs",
      storage: createJSONStorage(() => localStorage),
      version: 1,
      migrate: (persisted, version) => migrateEditorPrefs(persisted, version) as EditorPrefs,
    },
  ),
);
