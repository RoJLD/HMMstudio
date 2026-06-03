import { describe, it, expect } from "vitest";
import { migrateEditorPrefs } from "./editorPrefsStore";

describe("migrateEditorPrefs", () => {
  it("v0 showPriorPreview:true → overlayMode:'prior'", () => {
    expect(migrateEditorPrefs({ showPriorPreview: true }, 0)).toEqual({ overlayMode: "prior" });
  });
  it("v0 showPriorPreview:false → overlayMode:'none'", () => {
    expect(migrateEditorPrefs({ showPriorPreview: false }, 0)).toEqual({ overlayMode: "none" });
  });
  it("already-migrated state passes through", () => {
    expect(migrateEditorPrefs({ overlayMode: "learned" }, 1)).toEqual({ overlayMode: "learned" });
  });
});
