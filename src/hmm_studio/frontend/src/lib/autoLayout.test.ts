import { describe, it, expect } from "vitest";
import { autoLayout } from "./autoLayout";

type S = { id: string; name: string; position: { x: number; y: number } };

const states: S[] = [
  { id: "b", name: "s1", position: { x: 0, y: 0 } },
  { id: "a", name: "s0", position: { x: 0, y: 0 } },
  { id: "c", name: "s2", position: { x: 0, y: 0 } },
];

describe("autoLayout", () => {
  it("left-right: one row sorted by name, increasing x, constant y", () => {
    const pos = autoLayout(states, "left-right");
    expect(pos["a"].y).toBe(pos["b"].y);
    expect(pos["a"].x).toBeLessThan(pos["b"].x);
    expect(pos["b"].x).toBeLessThan(pos["c"].x);
  });

  it("circular: all on a circle (equal radius from the center)", () => {
    const pos = autoLayout(states, "circular");
    const xs = Object.values(pos).map((p) => p.x);
    const ys = Object.values(pos).map((p) => p.y);
    const cx = xs.reduce((a, b) => a + b, 0) / xs.length;
    const cy = ys.reduce((a, b) => a + b, 0) / ys.length;
    const radii = Object.values(pos).map((p) => Math.hypot(p.x - cx, p.y - cy));
    for (const r of radii) expect(r).toBeCloseTo(radii[0], 1);
  });

  it("returns a position for every state id", () => {
    const pos = autoLayout(states, "left-right");
    expect(Object.keys(pos).sort()).toEqual(["a", "b", "c"]);
  });
});
