import type { SavedTopology } from "../store/savedTopologiesStore";

const KIND = "hmm-studio-model-library";
const SCHEMA_VERSION = 1;

type Library = Record<string, SavedTopology>;
export type MergeMode = "keep-existing" | "overwrite";

/** Serialize the saved-models library to a portable JSON string. The envelope
 *  (schema_version + kind + models map) is forward-compatible with the future
 *  multi-tab docs-map (the `models` map IS that map). */
export function serializeLibrary(saved: Library): string {
  return JSON.stringify({ schema_version: SCHEMA_VERSION, kind: KIND, models: saved }, null, 2);
}

/** Parse + validate a library JSON. Returns `{ models }` on success or
 *  `{ error }` on malformed/wrong-kind input. Pure (no store access). */
export function parseLibrary(text: string): { models: Library | null; error: string | null } {
  let obj: unknown;
  try {
    obj = JSON.parse(text);
  } catch {
    return { models: null, error: "Not valid JSON." };
  }
  const o = obj as { kind?: unknown; models?: unknown };
  if (o.kind !== KIND) {
    return { models: null, error: `Wrong kind: expected "${KIND}".` };
  }
  if (!o.models || typeof o.models !== "object") {
    return { models: null, error: "Missing or invalid `models`." };
  }
  return { models: o.models as Library, error: null };
}

/** Merge an incoming library into the existing one. keep-existing (default)
 *  never overwrites a name already present; overwrite replaces same names. */
export function mergeModels(existing: Library, incoming: Library, mode: MergeMode): Library {
  if (mode === "overwrite") return { ...existing, ...incoming };
  return { ...incoming, ...existing }; // existing wins on key collision
}
