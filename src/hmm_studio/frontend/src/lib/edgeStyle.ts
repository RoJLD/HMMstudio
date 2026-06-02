import { MarkerType } from "reactflow";

/** Pure mapping `p in [0,1]` → React Flow edge style props: thickness ∝ p,
 *  opacity ∝ p, a 2-decimal label in a pill, and a closed arrowhead. Shared by
 *  the Results TransmatGraph (learned probabilities) and the editor's prior
 *  preview. The active/animated highlight is intentionally NOT here — it is a
 *  Results-only concern and stays local to TransmatGraph. */
export function probEdgeStyle(p: number) {
  return {
    label: p.toFixed(2),
    style: {
      strokeWidth: 1 + 5 * p,
      stroke: `rgba(79,70,229,${(0.3 + 0.7 * p).toFixed(2)})`,
    },
    labelStyle: { fontSize: 10, fontFamily: "monospace", fill: "#3730a3" },
    labelBgPadding: [2, 3] as [number, number],
    labelBgBorderRadius: 4,
    labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: "#6366f1",
      width: 16,
      height: 16,
    },
  };
}
