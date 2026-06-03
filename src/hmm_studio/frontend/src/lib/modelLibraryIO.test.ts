import { describe, it, expect } from "vitest";
import { serializeLibrary, parseLibrary, mergeModels } from "./modelLibraryIO";
import type { SavedTopology } from "../store/savedTopologiesStore";

const entry = (name: string): SavedTopology => ({
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

describe("modelLibraryIO", () => {
  it("serialize → parse round-trips the models", () => {
    const saved = { alpha: entry("alpha"), beta: entry("beta") };
    const json = serializeLibrary(saved);
    const parsed = parseLibrary(json);
    expect(parsed.error).toBeNull();
    expect(Object.keys(parsed.models!).sort()).toEqual(["alpha", "beta"]);
    expect(parsed.models!.alpha.data.name).toBe("alpha");
  });

  it("serialized payload carries schema_version + kind", () => {
    const obj = JSON.parse(serializeLibrary({ a: entry("a") }));
    expect(obj.schema_version).toBe(1);
    expect(obj.kind).toBe("hmm-studio-model-library");
  });

  it("parse rejects a wrong-kind payload", () => {
    expect(parseLibrary(JSON.stringify({ kind: "something-else", models: {} })).error).toMatch(/kind/i);
  });

  it("parse rejects malformed JSON", () => {
    expect(parseLibrary("{not json").error).toBeTruthy();
  });

  it("mergeModels keep-existing: incoming does not overwrite a same name", () => {
    const existing = { a: entry("a") };
    const incoming = { a: { ...entry("a"), savedAt: 999 }, b: entry("b") };
    const merged = mergeModels(existing, incoming, "keep-existing");
    expect(merged.a.savedAt).toBe(0); // kept
    expect(merged.b.name).toBe("b"); // added
  });

  it("mergeModels overwrite: incoming replaces a same name", () => {
    const existing = { a: entry("a") };
    const incoming = { a: { ...entry("a"), savedAt: 999 } };
    const merged = mergeModels(existing, incoming, "overwrite");
    expect(merged.a.savedAt).toBe(999);
  });
});
