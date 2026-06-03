import { describe, it, expect } from "vitest";
import { allowedTransitionsForShape } from "./buildTopologyYaml";

describe("allowedTransitionsForShape", () => {
  it("ergodic → every ordered pair including self-loops (K²)", () => {
    const names = ["s0", "s1", "s2"];
    const pairs = allowedTransitionsForShape("ergodic", names);
    expect(pairs).toHaveLength(9); // 3×3
    expect(pairs).toContainEqual(["s0", "s0"]);
    expect(pairs).toContainEqual(["s2", "s2"]);
    expect(pairs).toContainEqual(["s0", "s2"]);
    expect(pairs).toContainEqual(["s2", "s0"]);
  });

  it("left-right keeps self-loop + forward only", () => {
    const pairs = allowedTransitionsForShape("left-right", ["s0", "s1", "s2"]);
    expect(pairs).toContainEqual(["s0", "s0"]);
    expect(pairs).toContainEqual(["s0", "s1"]);
    expect(pairs).not.toContainEqual(["s1", "s0"]);
    expect(pairs).not.toContainEqual(["s0", "s2"]);
  });

  it("bakis adds skip-one", () => {
    const pairs = allowedTransitionsForShape("bakis", ["s0", "s1", "s2"]);
    expect(pairs).toContainEqual(["s0", "s2"]);
  });
});
