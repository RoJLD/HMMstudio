import { useSavedTopologies } from "../../store/savedTopologiesStore";

/** A toggled "My models" panel. This skeleton renders the list with Load/Delete
 *  per row; Export/Share (Task 4) and Import/Backup (Task 5) are added next. */
export function SavedModelsPanel({ onLoad, onClose }: { onLoad: (name: string) => void; onClose: () => void }) {
  const saved = useSavedTopologies((s) => s.saved);
  const removeModel = useSavedTopologies((s) => s.remove);
  const names = Object.keys(saved);

  return (
    <div className="absolute z-20 mt-1 w-80 max-h-80 overflow-auto rounded border border-slate-300 bg-white shadow-lg p-2 text-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-slate-700">My models ({names.length})</span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700" title="Close">✕</button>
      </div>
      {names.length === 0 && <p className="text-xs text-slate-400 px-1 py-2">No saved models yet.</p>}
      <ul className="space-y-1">
        {names.map((n) => (
          <li key={n} className="flex items-center gap-1 px-1 py-0.5 rounded hover:bg-slate-50">
            <span className="flex-1 truncate" title={n}>{n}</span>
            <button onClick={() => onLoad(n)} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100" title="Load into editor">Load</button>
            <button
              onClick={() => { if (window.confirm(`Delete saved model "${n}"?`)) removeModel(n); }}
              className="px-1.5 py-0.5 rounded border border-slate-200 text-red-600 hover:bg-red-50"
              title="Delete"
            >🗑</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
