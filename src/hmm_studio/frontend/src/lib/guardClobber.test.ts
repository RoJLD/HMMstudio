import { describe, it, expect, vi } from "vitest";
import { confirmClobber } from "./guardClobber";

describe("confirmClobber", () => {
  it("returns true immediately when the current model is empty (no prompt)", () => {
    const onSave = vi.fn();
    expect(confirmClobber(0, onSave, () => false)).toBe(true);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("non-empty + user cancels confirm → false (abort clobber)", () => {
    const onSave = vi.fn();
    expect(confirmClobber(3, onSave, () => false, () => false)).toBe(false);
  });

  it("non-empty + user chooses to save → calls onSave then returns true", () => {
    const onSave = vi.fn();
    expect(confirmClobber(3, onSave, () => true)).toBe(true);
    expect(onSave).toHaveBeenCalledOnce();
  });
});
