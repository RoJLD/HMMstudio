import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { useTopologyStore } from "../../store/topologyStore";

interface StateNodeData {
  label: string;
}

function StateNodeImpl({ id, data, selected }: NodeProps<StateNodeData>) {
  const renameState = useTopologyStore((s) => s.renameState);
  const addTransition = useTopologyStore((s) => s.addTransition);

  return (
    <div
      className={
        "relative px-4 py-2 rounded-full border-2 bg-white shadow-sm min-w-[80px] max-w-[160px] text-center " +
        (selected
          ? "border-brand-600 ring-2 ring-brand-500/30"
          : "border-slate-300")
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-brand-500 !w-2 !h-2"
      />
      <input
        value={data.label}
        onChange={(e) => renameState(id, e.target.value)}
        onClick={(e) => e.stopPropagation()}
        className="w-full bg-transparent text-center text-sm font-medium text-slate-900 outline-none truncate"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-brand-500 !w-2 !h-2"
      />
      {selected && (
        <button
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); addTransition(id, id); }}
          title="Add a self-transition (loop)"
          className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-brand-600 text-white text-xs leading-5 text-center shadow"
        >↺</button>
      )}
    </div>
  );
}

export const StateNode = memo(StateNodeImpl);
