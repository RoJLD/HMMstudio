import type { Node } from "reactflow";

interface StoreState {
  id: string;
  name: string;
  position: { x: number; y: number };
}

/** Merge the store's states into the existing React Flow node array BY ID.
 *  New states → fresh nodes; removed states → dropped; surviving states keep
 *  React Flow's transient fields (selected, dragging, positionAbsolute, measured
 *  width/height) while taking position + label from the store. This is what
 *  keeps the selection ring and measured layout alive across store commits. */
export function reconcileNodes(prev: Node[], states: StoreState[]): Node[] {
  const prevById = new Map(prev.map((n) => [n.id, n]));
  return states.map((s) => {
    const existing = prevById.get(s.id);
    if (existing) {
      return { ...existing, position: s.position, data: { label: s.name } };
    }
    return {
      id: s.id,
      type: "state",
      position: s.position,
      data: { label: s.name },
    } as Node;
  });
}
