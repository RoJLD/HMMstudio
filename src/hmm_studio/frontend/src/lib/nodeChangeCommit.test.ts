import { describe, it, expect } from "vitest";
import type { NodeChange } from "reactflow";
import { collectNodeCommits } from "./nodeChangeCommit";

describe("collectNodeCommits", () => {
  it("collects multiple finished drags into one batch", () => {
    const changes: NodeChange[] = [
      { type: "position", id: "a", position: { x: 1, y: 2 }, dragging: false },
      { type: "position", id: "b", position: { x: 3, y: 4 }, dragging: false },
    ];
    const { moved, removed } = collectNodeCommits(changes);
    expect(moved).toEqual({ a: { x: 1, y: 2 }, b: { x: 3, y: 4 } });
    expect(removed).toEqual([]);
  });

  it("ignores in-flight drag frames (dragging === true)", () => {
    const changes: NodeChange[] = [
      { type: "position", id: "a", position: { x: 9, y: 9 }, dragging: true },
    ];
    expect(collectNodeCommits(changes).moved).toEqual({});
  });

  it("ignores position changes without a final position", () => {
    const changes: NodeChange[] = [{ type: "position", id: "a", dragging: false }];
    expect(collectNodeCommits(changes).moved).toEqual({});
  });

  it("collects removals", () => {
    const changes: NodeChange[] = [
      { type: "remove", id: "x" },
      { type: "remove", id: "y" },
    ];
    expect(collectNodeCommits(changes).removed).toEqual(["x", "y"]);
  });

  it("handles a mixed batch (drop + remove + select)", () => {
    const changes: NodeChange[] = [
      { type: "position", id: "a", position: { x: 5, y: 6 }, dragging: false },
      { type: "remove", id: "z" },
      { type: "select", id: "b", selected: true },
    ];
    const { moved, removed } = collectNodeCommits(changes);
    expect(moved).toEqual({ a: { x: 5, y: 6 } });
    expect(removed).toEqual(["z"]);
  });
});
