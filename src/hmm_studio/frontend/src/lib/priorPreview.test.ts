import { describe, it, expect } from "vitest";
import { priorMeanPreview } from "./priorPreview";

type E = { id: string; source: string; target: string; prior_weight?: number };

describe("priorMeanPreview", () => {
  const twoOut: E[] = [
    { id: "e1", source: "a", target: "b" },
    { id: "e2", source: "a", target: "c" },
  ];

  it("no overrides → uniform 1/out-degree", () => {
    const m = priorMeanPreview(twoOut, 1);
    expect(m.get("e1")).toBeCloseTo(0.5);
    expect(m.get("e2")).toBeCloseTo(0.5);
  });

  it("is scale-invariant in global alpha with no overrides", () => {
    const a1 = priorMeanPreview(twoOut, 1);
    const a2 = priorMeanPreview(twoOut, 2);
    const a100 = priorMeanPreview(twoOut, 100);
    for (const id of ["e1", "e2"]) {
      expect(a2.get(id)).toBeCloseTo(a1.get(id)!);
      expect(a100.get(id)).toBeCloseTo(a1.get(id)!);
    }
  });

  it("MLE mode (globalAlpha null) → always uniform, ignoring stray overrides", () => {
    const withOverride: E[] = [
      { id: "e1", source: "a", target: "b", prior_weight: 5 },
      { id: "e2", source: "a", target: "c" },
    ];
    const m = priorMeanPreview(withOverride, null);
    expect(m.get("e1")).toBeCloseTo(0.5);
    expect(m.get("e2")).toBeCloseTo(0.5);
  });

  it("numeric globalAlpha + one override → weighted mean", () => {
    const withOverride: E[] = [
      { id: "e1", source: "a", target: "b", prior_weight: 3 },
      { id: "e2", source: "a", target: "c" }, // falls back to globalAlpha=1
    ];
    const m = priorMeanPreview(withOverride, 1);
    expect(m.get("e1")).toBeCloseTo(0.75); // 3 / (3+1)
    expect(m.get("e2")).toBeCloseTo(0.25);
  });

  it("a self-loop counts as an out-edge of its source", () => {
    const withSelf: E[] = [
      { id: "e1", source: "a", target: "a" },
      { id: "e2", source: "a", target: "b" },
    ];
    const m = priorMeanPreview(withSelf, 1);
    expect(m.get("e1")).toBeCloseTo(0.5);
    expect(m.get("e2")).toBeCloseTo(0.5);
  });
});
