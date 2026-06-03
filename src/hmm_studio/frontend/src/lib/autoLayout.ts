interface LayoutState { id: string; name: string }
export type LayoutMode = "left-right" | "circular";

/** Pure HMM-aware layouts. left-right = a single horizontal chain sorted by
 *  name (natural numeric order s0,s1,…); circular = evenly spaced on a circle
 *  (reuses the Results TransmatGraph radius formula). Returns id→position;
 *  the caller commits via setPositions (one undo entry). */
export function autoLayout(states: LayoutState[], mode: LayoutMode): Record<string, { x: number; y: number }> {
  const out: Record<string, { x: number; y: number }> = {};
  if (mode === "circular") {
    const K = states.length || 1;
    const R = Math.max(110, 26 * K);
    const cx = R + 70;
    const cy = R + 40;
    states.forEach((s, i) => {
      const a = (2 * Math.PI * i) / K - Math.PI / 2;
      out[s.id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) };
    });
    return out;
  }
  const sorted = [...states].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { numeric: true }),
  );
  const STEP = 240;
  const X0 = 60;
  const Y = 120;
  sorted.forEach((s, i) => {
    out[s.id] = { x: X0 + i * STEP, y: Y };
  });
  return out;
}
