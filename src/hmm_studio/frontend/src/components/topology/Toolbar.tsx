import { useTopologyStore, useTopologyTemporal } from "../../store/topologyStore";

interface ToolbarProps {
  onValidate: () => void;
  onExport: () => void;
  onImport: () => void;
}

export function Toolbar({ onValidate, onExport, onImport }: ToolbarProps) {
  const addState = useTopologyStore((s) => s.addState);
  const undo = useTopologyTemporal((s) => s.undo);
  const redo = useTopologyTemporal((s) => s.redo);
  const canUndo = useTopologyTemporal((s) => s.pastStates.length > 0);
  const canRedo = useTopologyTemporal((s) => s.futureStates.length > 0);

  const btn =
    "px-3 py-1.5 rounded text-sm border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex gap-2 items-center mb-2 flex-wrap">
      <button
        onClick={() =>
          addState({ x: 100 + Math.random() * 300, y: 100 + Math.random() * 200 })
        }
        className={btn}
      >
        + state
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={() => undo()} disabled={!canUndo} className={btn}>
        ↶ Undo
      </button>
      <button onClick={() => redo()} disabled={!canRedo} className={btn}>
        ↷ Redo
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={onImport} className={btn}>
        ↑ Import YAML
      </button>
      <button onClick={onExport} className={btn}>
        ↓ Export YAML
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={onValidate} className={btn}>
        ✓ Re-validate
      </button>
    </div>
  );
}
