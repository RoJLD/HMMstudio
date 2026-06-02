interface PreviewEdge {
  id: string;
  source: string;
  prior_weight?: number;
}

/** Per-edge Dirichlet prior MEAN = expected transition probability *before* any
 *  fit. Grouped by source node. Returns a Map edgeId → p.
 *
 *  - MLE mode (globalAlpha === null): ALWAYS uniform 1/out-degree per source —
 *    stray per-edge overrides are ignored (there is no global prior to weight
 *    against), so the display can honestly be labelled "uniform".
 *  - Otherwise: α_eff = prior_weight ?? globalAlpha; p = α_eff / Σ α_eff.
 *
 *  This is a MEAN, not a smoothing strength: it is invariant to the overall α
 *  magnitude. The UI labels it "prior mean (expected P before fit)" and must
 *  NOT present it as "what raising α does". */
export function priorMeanPreview(
  transitions: PreviewEdge[],
  globalAlpha: number | null,
): Map<string, number> {
  const bySource = new Map<string, PreviewEdge[]>();
  for (const t of transitions) {
    const arr = bySource.get(t.source) ?? [];
    arr.push(t);
    bySource.set(t.source, arr);
  }

  const result = new Map<string, number>();
  const mle = globalAlpha === null;
  for (const outs of bySource.values()) {
    const d = outs.length;
    if (d === 0) continue; // unreachable (an edge always has its source)
    if (mle) {
      for (const t of outs) result.set(t.id, 1 / d);
    } else {
      const alphaEff = (t: PreviewEdge) => t.prior_weight ?? globalAlpha;
      const sum = outs.reduce((acc, t) => acc + alphaEff(t)!, 0);
      for (const t of outs) result.set(t.id, alphaEff(t)! / sum);
    }
  }
  return result;
}
