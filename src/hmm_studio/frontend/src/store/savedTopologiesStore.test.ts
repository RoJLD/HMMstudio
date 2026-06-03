import { describe, it, expect, beforeEach } from "vitest";
import { useSavedTopologies, type SavedTopology } from "./savedTopologiesStore";

const demo = (name: string): SavedTopology => ({
  name,
  data: {
    name,
    states: [{ id: "a", name: "s0", position: { x: 0, y: 0 } }],
    transitions: [],
    emission: { type: "gaussian", n_features: 1, covariance_type: "full", n_mix: null, n_symbols: null },
    startprob: "uniform",
    init: { strategy: "kmeans", seed: 42 },
    fit: { algorithm: "baum_welch", n_iter: 200, tol: 1e-4 },
    transmat_prior_alpha: null,
  },
  savedAt: 0,
});

describe("savedTopologiesStore", () => {
  beforeEach(() => useSavedTopologies.setState({ saved: {} }));

  it("save then list", () => {
    useSavedTopologies.getState().save(demo("alpha"));
    expect(Object.keys(useSavedTopologies.getState().saved)).toEqual(["alpha"]);
  });

  it("save overwrites a same-name entry", () => {
    useSavedTopologies.getState().save(demo("alpha"));
    useSavedTopologies.getState().save(demo("alpha"));
    expect(Object.keys(useSavedTopologies.getState().saved)).toHaveLength(1);
  });

  it("remove deletes by name", () => {
    useSavedTopologies.getState().save(demo("alpha"));
    useSavedTopologies.getState().remove("alpha");
    expect(useSavedTopologies.getState().saved).toEqual({});
  });
});
