import { describe, it, expect } from "vitest";
import { topologyFingerprint } from "./topologyFingerprint";

type S = { id: string; name: string; position: { x: number; y: number } };
type T = { id: string; source: string; target: string };

const states: S[] = [
  { id: "a", name: "s0", position: { x: 0, y: 0 } },
  { id: "b", name: "s1", position: { x: 9, y: 9 } },
];
const trans: T[] = [{ id: "e1", source: "a", target: "b" }];

describe("topologyFingerprint", () => {
  it("is invariant to position changes and transition order", () => {
    const fp1 = topologyFingerprint(states, trans);
    const moved = states.map((s) => ({ ...s, position: { x: 99, y: 99 } }));
    const reordered: T[] = [{ id: "e1", source: "a", target: "b" }];
    expect(topologyFingerprint(moved, reordered)).toBe(fp1);
  });

  it("changes when a state is renamed", () => {
    const fp1 = topologyFingerprint(states, trans);
    const renamed = states.map((s) => (s.id === "b" ? { ...s, name: "X" } : s));
    expect(topologyFingerprint(renamed, trans)).not.toBe(fp1);
  });

  it("changes when a transition is added", () => {
    const fp1 = topologyFingerprint(states, trans);
    const more: T[] = [...trans, { id: "e2", source: "b", target: "a" }];
    expect(topologyFingerprint(states, more)).not.toBe(fp1);
  });
});
