import { describe, it, expect } from "vitest";
import type { Node } from "reactflow";
import { reconcileNodes } from "./reconcileNodes";

type S = { id: string; name: string; position: { x: number; y: number } };

describe("reconcileNodes", () => {
  it("creates nodes for new states", () => {
    const states: S[] = [{ id: "s1", name: "s0", position: { x: 0, y: 0 } }];
    const out = reconcileNodes([], states);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ id: "s1", type: "state", data: { label: "s0" } });
  });

  it("preserves selected/dragging/measured fields of existing nodes", () => {
    const prev: Node[] = [
      {
        id: "s1",
        type: "state",
        position: { x: 0, y: 0 },
        data: { label: "s0" },
        selected: true,
        dragging: true,
        width: 120,
        height: 40,
      } as Node,
    ];
    const states: S[] = [{ id: "s1", name: "renamed", position: { x: 10, y: 20 } }];
    const out = reconcileNodes(prev, states);
    expect(out[0].selected).toBe(true);
    expect(out[0].dragging).toBe(true);
    expect(out[0].width).toBe(120);
    expect(out[0].height).toBe(40);
    expect(out[0].position).toEqual({ x: 10, y: 20 });
    expect(out[0].data).toEqual({ label: "renamed" });
  });

  it("drops nodes whose state was removed", () => {
    const prev: Node[] = [
      { id: "s1", type: "state", position: { x: 0, y: 0 }, data: { label: "s0" } } as Node,
      { id: "s2", type: "state", position: { x: 0, y: 0 }, data: { label: "s1" } } as Node,
    ];
    const states: S[] = [{ id: "s2", name: "s1", position: { x: 0, y: 0 } }];
    const out = reconcileNodes(prev, states);
    expect(out.map((n) => n.id)).toEqual(["s2"]);
  });
});
