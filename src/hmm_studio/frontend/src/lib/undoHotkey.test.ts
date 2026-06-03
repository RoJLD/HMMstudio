import { describe, it, expect } from "vitest";
import { undoRedoIntent, isTextEntryTarget } from "./undoHotkey";

const chord = (over: Partial<Parameters<typeof undoRedoIntent>[0]>) => ({
  key: "z",
  ctrlKey: false,
  metaKey: false,
  shiftKey: false,
  ...over,
});

describe("undoRedoIntent", () => {
  it("maps Ctrl+Z to undo", () => {
    expect(undoRedoIntent(chord({ ctrlKey: true }))).toBe("undo");
  });

  it("maps Cmd+Z (metaKey) to undo", () => {
    expect(undoRedoIntent(chord({ metaKey: true }))).toBe("undo");
  });

  it("maps Ctrl+Shift+Z to redo", () => {
    expect(undoRedoIntent(chord({ ctrlKey: true, shiftKey: true }))).toBe("redo");
  });

  it("maps Ctrl+Y to redo (Windows convention)", () => {
    expect(undoRedoIntent(chord({ key: "y", ctrlKey: true }))).toBe("redo");
  });

  it("maps Cmd+Y (metaKey) to redo", () => {
    expect(undoRedoIntent(chord({ key: "y", metaKey: true }))).toBe("redo");
  });

  it("is case-insensitive on the key", () => {
    expect(undoRedoIntent(chord({ key: "Z", ctrlKey: true }))).toBe("undo");
  });

  it("returns null without a modifier", () => {
    expect(undoRedoIntent(chord({ key: "z" }))).toBeNull();
  });

  it("returns null for unrelated keys", () => {
    expect(undoRedoIntent(chord({ key: "a", ctrlKey: true }))).toBeNull();
  });
});

describe("isTextEntryTarget", () => {
  it("is true for an input", () => {
    expect(isTextEntryTarget({ tagName: "INPUT" } as unknown as EventTarget)).toBe(true);
  });

  it("is true for a textarea", () => {
    expect(isTextEntryTarget({ tagName: "TEXTAREA" } as unknown as EventTarget)).toBe(true);
  });

  it("is true for a contentEditable element", () => {
    expect(
      isTextEntryTarget({ tagName: "DIV", isContentEditable: true } as unknown as EventTarget),
    ).toBe(true);
  });

  it("is false for a plain div and for null", () => {
    expect(isTextEntryTarget({ tagName: "DIV" } as unknown as EventTarget)).toBe(false);
    expect(isTextEntryTarget(null)).toBe(false);
  });
});
