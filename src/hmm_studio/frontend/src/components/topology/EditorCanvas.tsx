import { useCallback, useEffect, useState } from "react";
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
import { reconcileNodes } from "../../lib/reconcileNodes";
import { probEdgeStyle } from "../../lib/edgeStyle";
import { priorMeanPreview } from "../../lib/priorPreview";
import { useEditorPrefs } from "../../store/editorPrefsStore";
import { getFitTransmat, type TransmatResponse } from "../../api/client";
import { useFitLink } from "../../store/fitLinkStore";
import { buildLearnedMap } from "../../lib/learnedOverlay";
import { topologyFingerprint } from "../../lib/topologyFingerprint";

export function EditorCanvas() {
  const states = useTopologyStore((s) => s.states);
  const transitions = useTopologyStore((s) => s.transitions);
  const moveState = useTopologyStore((s) => s.moveState);
  const removeState = useTopologyStore((s) => s.removeState);
  const addTransition = useTopologyStore((s) => s.addTransition);
  const removeTransition = useTopologyStore((s) => s.removeTransition);
  const setSelectedStateId = useTopologyStore((s) => s.setSelectedStateId);
  const setSelectedEdgeId = useTopologyStore((s) => s.setSelectedEdgeId);
  const transmatPriorAlpha = useTopologyStore((s) => s.transmat_prior_alpha);
  const overlayMode = useEditorPrefs((s) => s.overlayMode);

  const lastFitJobId = useFitLink((s) => s.lastFitJobId);
  const fitFingerprint = useFitLink((s) => s.fitFingerprint);
  const [learnedTransmat, setLearnedTransmat] = useState<TransmatResponse | null>(null);
  const [learnedError, setLearnedError] = useState<string | null>(null);

  useEffect(() => {
    if (overlayMode !== "learned" || !lastFitJobId) {
      setLearnedTransmat(null);
      setLearnedError(null);
      return;
    }
    let cancelled = false;
    getFitTransmat(lastFitJobId)
      .then((t) => { if (!cancelled) { setLearnedTransmat(t); setLearnedError(null); } })
      .catch((e) => { if (!cancelled) { setLearnedTransmat(null); setLearnedError(e instanceof Error ? e.message : "fetch failed"); } });
    return () => { cancelled = true; };
  }, [overlayMode, lastFitJobId]);

  const currentFingerprint = topologyFingerprint(states, transitions);
  const learnedStale =
    overlayMode === "learned" && fitFingerprint !== null && fitFingerprint !== currentFingerprint;
  const learnedMap =
    overlayMode === "learned" && learnedTransmat && !learnedStale
      ? buildLearnedMap(transitions, states, learnedTransmat)
      : null;

  const [rfNodes, setRfNodes] = useState<Node[]>(() => reconcileNodes([], states));

  // Re-seed local nodes whenever the store's states identity changes (commit,
  // add, remove, YAML load). Merge-by-id preserves React Flow's transient
  // fields (selected, dragging, measured size) — see reconcileNodes.
  useEffect(() => {
    setRfNodes((prev) => reconcileNodes(prev, states));
  }, [states]);

  const previews =
    overlayMode === "prior" ? priorMeanPreview(transitions, transmatPriorAlpha) : null;

  const edges: Edge[] = transitions.map((t) => {
    if (learnedMap) {
      const p = learnedMap.get(t.id) ?? 0;
      return { ...probEdgeStyle(p), id: t.id, source: t.source, target: t.target, type: "default" };
    }
    if (previews) {
      const p = previews.get(t.id) ?? 0;
      return {
        ...probEdgeStyle(p),
        id: t.id,
        source: t.source,
        target: t.target,
        type: "default",
      };
    }
    return {
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
    };
  });

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      // Apply every change type to the local array so in-flight drags AND
      // selection render. setRfNodes uses the functional updater to avoid a
      // stale closure.
      setRfNodes((nds) => applyNodeChanges(changes, nds));
      // Commit side effects to the store: final drag position (once, on
      // drop) and removals.
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
    },
    [moveState, removeState],
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
    <div className="flex-1 border border-slate-200 rounded relative">
      {overlayMode === "learned" && (learnedStale || !lastFitJobId || learnedError) && (
        <div className="absolute z-10 m-2 px-2 py-1 text-xs rounded bg-amber-50 border border-amber-300 text-amber-800">
          {!lastFitJobId
            ? "No fit yet — click ▶ Fit this topology to compute learned probabilities."
            : learnedStale
              ? "Topology changed since the last fit — re-fit to refresh the learned probabilities."
              : `Could not load learned probabilities: ${learnedError}`}
        </div>
      )}
      <ReactFlow
        nodes={rfNodes}
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
