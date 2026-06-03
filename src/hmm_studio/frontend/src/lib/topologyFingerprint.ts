interface FpState { id: string; name: string }
interface FpEdge { source: string; target: string }

/** Stable identity of a topology's STRUCTURE (names + edges), independent of
 *  node positions and edge order. Used to detect "the topology changed since
 *  the fit" so a learned-probability overlay can be shown only when it still
 *  matches. Names are the join key that survives the fit YAML round-trip. */
export function topologyFingerprint(states: FpState[], transitions: FpEdge[]): string {
  const idToName = new Map(states.map((s) => [s.id, s.name]));
  const names = states.map((s) => s.name).slice().sort();
  const pairs = transitions
    .map((t) => `${idToName.get(t.source) ?? t.source}>${idToName.get(t.target) ?? t.target}`)
    .sort();
  return JSON.stringify({ names, pairs });
}
