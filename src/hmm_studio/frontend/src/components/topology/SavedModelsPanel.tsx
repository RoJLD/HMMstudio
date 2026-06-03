import { useSavedTopologies } from "../../store/savedTopologiesStore";
import { topologyToYAML } from "../../lib/yaml";
import { buildShareUrl } from "../../lib/share";

/** A toggled "My models" panel. Each row has Load / Export YAML / Share / Delete.
 *  Import/Backup (Task 5) is added next. */
export function SavedModelsPanel({ onLoad, onClose }: { onLoad: (name: string) => void; onClose: () => void }) {
  const saved = useSavedTopologies((s) => s.saved);
  const removeModel = useSavedTopologies((s) => s.remove);
  const names = Object.keys(saved);

  function exportModel(name: string) {
    const entry = saved[name];
    if (!entry) return;
    const blob = new Blob([topologyToYAML(entry.data)], { type: "application/x-yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name || "model"}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function shareModel(name: string) {
    const entry = saved[name];
    if (!entry) return;
    const url = buildShareUrl(entry.data);
    try {
      await navigator.clipboard.writeText(url);
      // eslint-disable-next-line no-alert
      alert("Share link copied to clipboard.");
    } catch {
      // eslint-disable-next-line no-alert
      alert("Copy failed — URL:\n" + url);
    }
  }

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
            <button onClick={() => exportModel(n)} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100" title="Download as .yaml">⬇ YAML</button>
            <button onClick={() => shareModel(n)} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100" title="Copy a share URL">⎘</button>
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
