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
import type { TransmatResponse } from "../../api/client";

// Edges below this probability are hidden to keep the graph readable.
const MIN_PROB = 0.01;

interface GraphNodeData {
  label: string;
}

// Read-only state node (decoupled from the editable topology StateNode + store).
const GraphStateNode = memo(({ data }: NodeProps<GraphNodeData>) => (
  <div className="px-4 py-2 rounded-full border-2 border-slate-300 bg-white shadow-sm min-w-[72px] text-center text-sm font-medium text-slate-900">
    <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
    {data.label}
    <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
  </div>
));
GraphStateNode.displayName = "GraphStateNode";

const graphNodeTypes: NodeTypes = { gstate: GraphStateNode };

/** Read-only node-graph of a fitted transition matrix: arrows + probability
 *  bubbles + edge thickness. Complements the precise heatmap with an intuitive
 *  view. Nodes are auto-laid-out on a circle (transmat carries no positions). */
export function TransmatGraph({ data }: { data: TransmatResponse }) {
  const K = data.n_states;
  const R = Math.max(110, 26 * K);
  const cx = R + 70;
  const cy = R + 40;

  const nodes: Node[] = data.state_names.map((name, i) => {
    const a = (2 * Math.PI * i) / K - Math.PI / 2;
    return {
      id: `s${i}`,
      type: "gstate",
      position: { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) },
      data: { label: name },
    };
  });

  const edges: Edge[] = [];
  for (let i = 0; i < K; i++) {
    for (let j = 0; j < K; j++) {
      if (!data.mask[i]?.[j]) continue;
      const p = data.transmat[i]?.[j] ?? 0;
      if (p < MIN_PROB) continue;
      edges.push({
        id: `${i}-${j}`,
        source: `s${i}`,
        target: `s${j}`,
        label: p.toFixed(2),
        style: {
          strokeWidth: 1 + 5 * p,
          stroke: `rgba(79,70,229,${(0.3 + 0.7 * p).toFixed(2)})`,
        },
        labelStyle: { fontSize: 10, fontFamily: "monospace", fill: "#3730a3" },
        labelBgPadding: [2, 3] as [number, number],
        labelBgBorderRadius: 4,
        labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#4f46e5", width: 16, height: 16 },
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
