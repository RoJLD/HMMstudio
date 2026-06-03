import type { NodeChange } from "reactflow";

export interface NodeCommits {
  /** Finished drags (drop), keyed by node id → final position. */
  moved: Record<string, { x: number; y: number }>;
  /** Node ids removed in this batch. */
  removed: string[];
}

/**
 * Split a React Flow change batch into the side effects that must reach the
 * store: finished drags (so a multi-node move commits as ONE undo entry via
 * setPositions) and removals. In-flight drag frames (`dragging !== false`) are
 * intentionally ignored — they only update the local render mirror.
 */
export function collectNodeCommits(changes: NodeChange[]): NodeCommits {
  const moved: Record<string, { x: number; y: number }> = {};
  const removed: string[] = [];
  for (const c of changes) {
    if (c.type === "position" && c.position && c.dragging === false) {
      moved[c.id] = c.position;
    } else if (c.type === "remove") {
      removed.push(c.id);
    }
  }
  return { moved, removed };
}
