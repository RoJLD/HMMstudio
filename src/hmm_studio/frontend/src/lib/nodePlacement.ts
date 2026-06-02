interface Positioned {
  position: { x: number; y: number };
}

/** Lowest unused `s<N>` name, so deleting a middle state then adding one reuses
 *  the freed index instead of duplicating a name. */
export function lowestFreeStateName(states: { name: string }[]): string {
  const used = new Set(states.map((s) => s.name));
  let i = 0;
  while (used.has(`s${i}`)) i++;
  return `s${i}`;
}

/** A canvas position that does not overlap an existing node: start at a fixed
 *  anchor and nudge diagonally until clear. Deterministic (no Math.random). */
export function nextFreePosition(states: Positioned[]): { x: number; y: number } {
  const STEP = 40;
  const THRESHOLD = 60;
  let pos = { x: 120, y: 120 };
  const collides = (p: { x: number; y: number }) =>
    states.some(
      (s) =>
        Math.abs(s.position.x - p.x) < THRESHOLD &&
        Math.abs(s.position.y - p.y) < THRESHOLD,
    );
  let guard = 0;
  while (collides(pos) && guard++ < 200) {
    pos = { x: pos.x + STEP, y: pos.y + STEP };
  }
  return pos;
}
