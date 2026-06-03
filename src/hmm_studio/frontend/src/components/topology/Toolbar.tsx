import { useTopologyStore, useTopologyTemporal } from "../../store/topologyStore";
import { useSavedTopologies } from "../../store/savedTopologiesStore";
import { nextFreePosition } from "../../lib/nodePlacement";
import { useEditorPrefs } from "../../store/editorPrefsStore";

interface ToolbarProps {
  onValidate: () => void;
  onExport: () => void;
  onImport: () => void;
  onShare: () => void;
}

export function Toolbar({ onValidate, onExport, onImport, onShare }: ToolbarProps) {
  const addState = useTopologyStore((s) => s.addState);
  const states = useTopologyStore((s) => s.states);
  const undo = useTopologyTemporal((s) => s.undo);
  const redo = useTopologyTemporal((s) => s.redo);
  const canUndo = useTopologyTemporal((s) => s.pastStates.length > 0);
  const canRedo = useTopologyTemporal((s) => s.futureStates.length > 0);

  const showPriorPreview = useEditorPrefs((s) => s.showPriorPreview);
  const setShowPriorPreview = useEditorPrefs((s) => s.setShowPriorPreview);

  const saved = useSavedTopologies((s) => s.saved);
  const saveModel = useSavedTopologies((s) => s.save);
  const removeModel = useSavedTopologies((s) => s.remove);

  function handleSaveCurrent() {
    const st = useTopologyStore.getState();
    if (st.states.length === 0) return;
    const name = window.prompt("Save current model as:", st.name || "untitled");
    if (!name) return;
    saveModel({
      name,
      data: {
        name,
        states: st.states,
        transitions: st.transitions,
        emission: st.emission,
        startprob: st.startprob,
        init: st.init,
        fit: st.fit,
        transmat_prior_alpha: st.transmat_prior_alpha,
      },
      savedAt: Date.now(),
    });
  }

  function handleLoadSaved(name: string) {
    const entry = saved[name];
    if (!entry) return;
    useTopologyStore.getState().loadTopology(entry.data);
  }

  const btn =
    "px-3 py-1.5 rounded text-sm border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex gap-2 items-center mb-2 flex-wrap">
      <button
        onClick={() => addState(nextFreePosition(states))}
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
      <button onClick={onShare} className={btn}>
        ⎘ Share URL
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={onValidate} className={btn}>
        ✓ Re-validate
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <label className="flex items-center gap-1.5 text-sm text-slate-600 select-none">
        <input
          type="checkbox"
          checked={showPriorPreview}
          onChange={(e) => setShowPriorPreview(e.target.checked)}
        />
        prior preview
        <span className="text-xs text-slate-400">(expected P before fit)</span>
      </label>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={handleSaveCurrent} className={btn}>💾 Save model</button>
      <select
        className={btn}
        value=""
        onChange={(e) => {
          const v = e.target.value;
          if (v) handleLoadSaved(v);
          e.target.value = "";
        }}
      >
        <option value="">📂 Load saved…</option>
        {Object.keys(saved).map((n) => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>
      {Object.keys(saved).length > 0 && (
        <select
          className={btn}
          value=""
          onChange={(e) => {
            const v = e.target.value;
            if (v && window.confirm(`Delete saved model "${v}"?`)) removeModel(v);
            e.target.value = "";
          }}
        >
          <option value="">🗑 Delete…</option>
          {Object.keys(saved).map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      )}
    </div>
  );
}
