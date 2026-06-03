import { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  Connection,
  Edge,
  MarkerType,
  Node,
  NodeChange,
  applyNodeChanges,
  EdgeChange,
  applyEdgeChanges,
} from "reactflow";
import "reactflow/dist/style.css";
import { nodeTypes } from "./nodeTypes";
import { useTopologyStore } from "../../store/topologyStore";

export function EditorCanvas() {
  const states = useTopologyStore((s) => s.states);
  const transitions = useTopologyStore((s) => s.transitions);
  const moveState = useTopologyStore((s) => s.moveState);
  const removeState = useTopologyStore((s) => s.removeState);
  const addTransition = useTopologyStore((s) => s.addTransition);
  const removeTransition = useTopologyStore((s) => s.removeTransition);
  const setSelectedStateId = useTopologyStore((s) => s.setSelectedStateId);
  const setSelectedEdgeId = useTopologyStore((s) => s.setSelectedEdgeId);

  const nodes: Node[] = states.map((s) => ({
    id: s.id,
    type: "state",
    position: s.position,
    data: { label: s.name },
  }));

  const edges: Edge[] = transitions.map((t) => ({
    id: t.id,
    source: t.source,
    target: t.target,
    type: "default",
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: t.prior_weight !== undefined ? "#4f46e5" : "#94a3b8",
    },
    style: {
      strokeWidth: t.prior_weight !== undefined ? 3 : 2,
      stroke: t.prior_weight !== undefined ? "#4f46e5" : "#94a3b8",
    },
    label:
      t.prior_weight !== undefined ? `α=${t.prior_weight.toFixed(1)}` : undefined,
    labelStyle: { fontSize: 10, fontFamily: "monospace" },
    labelBgPadding: [2, 4] as [number, number],
    labelBgBorderRadius: 4,
    labelBgStyle: { fill: "#eef2ff", fillOpacity: 0.9 },
  }));

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      changes.forEach((change) => {
        if (
          change.type === "position" &&
          change.position &&
          change.dragging === false
        ) {
          moveState(change.id, change.position);
        }
        if (change.type === "remove") {
          removeState(change.id);
        }
      });
      // Apply locally too so the canvas reflects in-flight drags
      applyNodeChanges(changes, nodes);
    },
    [moveState, removeState, nodes],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "remove") removeTransition(change.id);
      });
      applyEdgeChanges(changes, edges);
    },
    [removeTransition, edges],
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      if (conn.source && conn.target) addTransition(conn.source, conn.target);
    },
    [addTransition],
  );

  const onSelectionChange = useCallback(
    ({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) => {
      setSelectedStateId(nodes[0]?.id ?? null);
      setSelectedEdgeId(nodes[0] ? null : edges[0]?.id ?? null);
    },
    [setSelectedStateId, setSelectedEdgeId],
  );

  return (
    <div className="flex-1 border border-slate-200 rounded">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onSelectionChange={onSelectionChange}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 1 }}
        deleteKeyCode={["Backspace", "Delete"]}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
