import { describe, it, expect } from "vitest";
import { buildLearnedMap } from "./learnedOverlay";

type S = { id: string; name: string };
type T = { id: string; source: string; target: string };

const states: S[] = [
  { id: "ida", name: "s0" },
  { id: "idb", name: "s1" },
];
const trans: T[] = [
  { id: "e_self", source: "ida", target: "ida" },
  { id: "e_fwd", source: "ida", target: "idb" },
];
const transmat = {
  state_names: ["s0", "s1"],
  transmat: [
    [0.8, 0.2],
    [0.3, 0.7],
  ],
  mask: [
    [true, true],
    [true, true],
  ],
  n_states: 2,
};

describe("buildLearnedMap", () => {
  it("maps each edge to transmat[i][j] via state name", () => {
    const m = buildLearnedMap(trans, states, transmat);
    expect(m.get("e_self")).toBeCloseTo(0.8); // s0→s0
    expect(m.get("e_fwd")).toBeCloseTo(0.2); // s0→s1
  });

  it("skips edges whose state name is not in the fitted matrix", () => {
    const extra: T[] = [...trans, { id: "e_x", source: "idGhost", target: "idb" }];
    const statesX: S[] = [...states, { id: "idGhost", name: "ghost" }];
    const m = buildLearnedMap(extra, statesX, transmat);
    expect(m.has("e_x")).toBe(false);
  });
});
