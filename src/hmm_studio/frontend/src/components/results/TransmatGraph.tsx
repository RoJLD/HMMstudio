import { memo } from "react";
import ReactFlow, {
  Background,
  Handle,
  Position,
  MarkerType,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";
import type { TransmatResponse, DecodedResponse } from "../../api/client";

// Edges below this probability are hidden to keep the graph readable.
const MIN_PROB = 0.01;

// Same state palette as ViterbiTimeline so the lit node matches the timeline.
const PALETTE = [
  "#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
  "#8b5cf6", "#ec4899", "#84cc16", "#f97316", "#0ea5e9",
];

function hexA(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

interface GraphNodeData {
  label: string;
  prob?: number; // posterior at the current cursor (animated mode)
  color?: string;
  active?: boolean; // the current Viterbi state at the cursor
}

// Read-only state node (decoupled from the editable topology StateNode + store).
const GraphStateNode = memo(({ data }: NodeProps<GraphNodeData>) => {
  const animated = data.prob != null && data.color != null;
  const bg = animated ? hexA(data.color as string, 0.12 + 0.6 * (data.prob ?? 0)) : "white";
  return (
    <div
      className={
        "px-4 py-2 rounded-full border-2 shadow-sm min-w-[72px] text-center text-sm font-medium text-slate-900 " +
        (data.active
          ? "border-brand-600 ring-2 ring-brand-500/40 font-semibold"
          : "border-slate-300")
      }
      style={{ background: bg }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
      {data.label}
      {animated && (
        <span className="block text-[10px] font-mono text-slate-500">
          {(data.prob ?? 0).toFixed(2)}
        </span>
      )}
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  );
});
GraphStateNode.displayName = "GraphStateNode";

const graphNodeTypes: NodeTypes = { gstate: GraphStateNode };

/** Read-only node-graph of a fitted transition matrix: arrows + probability
 *  bubbles + edge thickness. When `decoded` + `currentT` are supplied it
 *  animates with the timeline player: node fills = posterior[t], the current
 *  Viterbi state is ringed, and the active transition edge is highlighted. */
export function TransmatGraph({
  data,
  decoded,
  currentT,
}: {
  data: TransmatResponse;
  decoded?: DecodedResponse | null;
  currentT?: number | null;
}) {
  const K = data.n_states;
  const R = Math.max(110, 26 * K);
  const cx = R + 70;
  const cy = R + 40;

  // Map the full-T cursor into the downsampled decoded arrays (as ViterbiTimeline does).
  const hasCursor =
    decoded != null && currentT != null && decoded.viterbi.length > 0 && decoded.step > 0;
  const idx = hasCursor
    ? Math.min(decoded!.viterbi.length - 1, Math.max(0, Math.floor(currentT! / decoded!.step)))
    : null;
  const curState = idx != null ? decoded!.viterbi[idx] : null;
  const prevState = idx != null && idx > 0 ? decoded!.viterbi[idx - 1] : null;
  const post = idx != null ? decoded!.posterior[idx] : null;

  const nodes: Node[] = data.state_names.map((name, i) => {
    const a = (2 * Math.PI * i) / K - Math.PI / 2;
    return {
      id: `s${i}`,
      type: "gstate",
      position: { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) },
      data: {
        label: name,
        prob: post ? post[i] : undefined,
        color: post ? PALETTE[i % PALETTE.length] : undefined,
        active: curState === i,
      },
    };
  });

  const edges: Edge[] = [];
  for (let i = 0; i < K; i++) {
    for (let j = 0; j < K; j++) {
      if (!data.mask[i]?.[j]) continue;
      const p = data.transmat[i]?.[j] ?? 0;
      if (p < MIN_PROB) continue;
      const isActive = prevState != null && curState != null && i === prevState && j === curState;
      edges.push({
        id: `${i}-${j}`,
        source: `s${i}`,
        target: `s${j}`,
        label: p.toFixed(2),
        animated: isActive,
        style: {
          strokeWidth: isActive ? 4 : 1 + 5 * p,
          stroke: isActive ? "#4f46e5" : `rgba(79,70,229,${(0.3 + 0.7 * p).toFixed(2)})`,
        },
        labelStyle: { fontSize: 10, fontFamily: "monospace", fill: "#3730a3" },
        labelBgPadding: [2, 3] as [number, number],
        labelBgBorderRadius: 4,
        labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isActive ? "#4f46e5" : "#6366f1",
          width: 16,
          height: 16,
        },
      });
    }
  }

  return (
    <div
      style={{ height: Math.max(280, 2 * cy) }}
      className="border border-slate-200 rounded bg-slate-50/40"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={graphNodeTypes}
        fitView
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
      </ReactFlow>
    </div>
  );
}
