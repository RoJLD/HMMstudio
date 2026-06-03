import { useRef } from "react";
import { useSavedTopologies } from "../../store/savedTopologiesStore";
import { topologyToYAML, yamlToTopology } from "../../lib/yaml";
import { buildShareUrl } from "../../lib/share";
import { serializeLibrary, parseLibrary, mergeModels } from "../../lib/modelLibraryIO";

/** A toggled "My models" panel. Each row has Load / Export YAML / Share / Delete.
 *  Import model (.yaml), Export all (JSON), Import library (JSON merge) added in Task 5. */
export function SavedModelsPanel({ onLoad, onClose }: { onLoad: (name: string) => void; onClose: () => void }) {
  const saved = useSavedTopologies((s) => s.saved);
  const removeModel = useSavedTopologies((s) => s.remove);
  const saveModel = useSavedTopologies((s) => s.save);
  const setSaved = useSavedTopologies((s) => s.setSaved);
  const names = Object.keys(saved);

  const yamlInputRef = useRef<HTMLInputElement | null>(null);
  const jsonInputRef = useRef<HTMLInputElement | null>(null);

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

  function importModelFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const partial = yamlToTopology(String(reader.result));
        const proposed = (partial.name as string) || "imported";
        const name = window.prompt("Save imported model as:", proposed);
        if (!name) return;
        if (saved[name] && !window.confirm(`"${name}" exists — overwrite?`)) return;
        saveModel({
          name,
          data: {
            name,
            states: partial.states ?? [],
            transitions: partial.transitions ?? [],
            emission: partial.emission!,
            startprob: partial.startprob ?? "uniform",
            init: partial.init!,
            fit: partial.fit!,
            transmat_prior_alpha: partial.transmat_prior_alpha ?? null,
          },
          savedAt: Date.now(),
        });
      } catch (e) {
        // eslint-disable-next-line no-alert
        alert(`Import failed: ${e instanceof Error ? e.message : "?"}`);
      }
    };
    reader.readAsText(file);
  }

  function exportLibrary() {
    const blob = new Blob([serializeLibrary(saved)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "hmm-studio-models.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function importLibraryFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const { models, error } = parseLibrary(String(reader.result));
      if (error || !models) {
        // eslint-disable-next-line no-alert
        alert(`Import failed: ${error ?? "invalid library"}`);
        return;
      }
      const overwrite = window.confirm("Overwrite models with the same name? (Cancel = keep existing)");
      setSaved(mergeModels(saved, models, overwrite ? "overwrite" : "keep-existing"));
    };
    reader.readAsText(file);
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
      <div className="flex gap-1 mt-2 pt-2 border-t border-slate-200">
        <button onClick={() => yamlInputRef.current?.click()} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-xs" title="Import a .yaml model into the library">↑ Import model</button>
        <button onClick={exportLibrary} disabled={names.length === 0} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-xs disabled:opacity-40" title="Download the whole library as JSON">⬇ Export all</button>
        <button onClick={() => jsonInputRef.current?.click()} className="px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-100 text-xs" title="Import a library JSON (merge)">↑ Import library</button>
      </div>
      <input ref={yamlInputRef} type="file" accept=".yaml,.yml" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) importModelFile(f); e.target.value = ""; }} />
      <input ref={jsonInputRef} type="file" accept=".json" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) importLibraryFile(f); e.target.value = ""; }} />
    </div>
  );
}
