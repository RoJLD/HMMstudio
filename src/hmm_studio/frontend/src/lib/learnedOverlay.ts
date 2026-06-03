import type { TransmatResponse } from "../api/client";

interface OvState { id: string; name: string }
interface OvEdge { id: string; source: string; target: string }

/** Map each editor transition edge id → learned probability transmat[i][j],
 *  joining by STATE NAME (the only key that survives the fit YAML round-trip:
 *  matrix index i == position of a name in state_names). Edges whose endpoint
 *  names are not in the fitted matrix are omitted (caller styles them as
 *  absent). Self-loops (name==name) read transmat[i][i] naturally. */
export function buildLearnedMap(
  transitions: OvEdge[],
  states: OvState[],
  transmat: TransmatResponse,
): Map<string, number> {
  const idToName = new Map(states.map((s) => [s.id, s.name]));
  const nameToIdx = new Map(transmat.state_names.map((n, i) => [n, i]));
  const out = new Map<string, number>();
  for (const t of transitions) {
    const i = nameToIdx.get(idToName.get(t.source) ?? "");
    const j = nameToIdx.get(idToName.get(t.target) ?? "");
    if (i === undefined || j === undefined) continue;
    const row = transmat.transmat[i];
    if (!row || typeof row[j] !== "number") continue;
    out.set(t.id, row[j]);
  }
  return out;
}
