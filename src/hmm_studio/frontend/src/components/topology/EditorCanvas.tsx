import { useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  Connection,
  Edge,
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
    style: { strokeWidth: 2 },
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

  return (
    <div className="flex-1 border border-slate-200 rounded">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        deleteKeyCode={["Backspace", "Delete"]}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
