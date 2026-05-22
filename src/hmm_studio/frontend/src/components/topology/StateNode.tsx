import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { useTopologyStore } from "../../store/topologyStore";

interface StateNodeData {
  label: string;
}

function StateNodeImpl({ id, data, selected }: NodeProps<StateNodeData>) {
  const renameState = useTopologyStore((s) => s.renameState);

  return (
    <div
      className={
        "px-4 py-2 rounded-full border-2 bg-white shadow-sm min-w-[80px] text-center " +
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
        className="w-full bg-transparent text-center text-sm font-medium text-slate-900 outline-none"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-brand-500 !w-2 !h-2"
      />
    </div>
  );
}

export const StateNode = memo(StateNodeImpl);
