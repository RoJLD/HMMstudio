export type UndoRedoIntent = "undo" | "redo" | null;

/** A minimal view of a keydown event — keeps this helper pure and easy to test. */
export interface KeyChord {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  shiftKey: boolean;
}

/**
 * Map a keyboard chord to an undo/redo intent, returning null for anything else.
 *
 * - Ctrl/Cmd + Z         → undo
 * - Ctrl/Cmd + Shift + Z → redo
 * - Ctrl/Cmd + Y         → redo (Windows convention)
 *
 * React Flow does NOT bind these natively, so the editor wires them itself; the
 * intent it returns is fed to the already-wired zundo temporal store.
 */
export function undoRedoIntent(e: KeyChord): UndoRedoIntent {
  const mod = e.ctrlKey || e.metaKey;
  if (!mod) return null;
  const k = e.key.toLowerCase();
  if (k === "z") return e.shiftKey ? "redo" : "undo";
  if (k === "y") return "redo";
  return null;
}

/**
 * True when the event originated from a text-entry surface, where Ctrl+Z must
 * keep its native "undo typing" behaviour and not steal it for the canvas.
 */
export function isTextEntryTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || !el.tagName) return false;
  return el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable === true;
}
