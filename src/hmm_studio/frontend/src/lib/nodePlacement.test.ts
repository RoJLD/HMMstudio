import { describe, it, expect } from "vitest";
import { nextFreePosition, lowestFreeStateName } from "./nodePlacement";

describe("lowestFreeStateName", () => {
  it("empty → s0", () => {
    expect(lowestFreeStateName([])).toBe("s0");
  });
  it("contiguous → next index", () => {
    expect(lowestFreeStateName([{ name: "s0" }, { name: "s1" }])).toBe("s2");
  });
  it("fills the gap left by a deletion", () => {
    expect(lowestFreeStateName([{ name: "s0" }, { name: "s2" }])).toBe("s1");
  });
});

describe("nextFreePosition", () => {
  it("empty canvas → the base anchor", () => {
    expect(nextFreePosition([])).toEqual({ x: 120, y: 120 });
  });
  it("nudges away from an occupied anchor", () => {
    const pos = nextFreePosition([{ position: { x: 120, y: 120 } }]);
    expect(pos.x).toBeGreaterThan(120);
    expect(pos.y).toBeGreaterThan(120);
  });
});
