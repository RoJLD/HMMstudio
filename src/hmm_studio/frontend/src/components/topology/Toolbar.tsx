import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTopologyStore, useTopologyTemporal } from "../../store/topologyStore";
import { useSavedTopologies } from "../../store/savedTopologiesStore";
import { nextFreePosition } from "../../lib/nodePlacement";
import { useEditorPrefs, type OverlayMode } from "../../store/editorPrefsStore";
import { useDatasetStore } from "../../store/datasetStore";
import { startFit } from "../../api/client";
import { topologyToYAML } from "../../lib/yaml";
import { topologyFingerprint } from "../../lib/topologyFingerprint";
import { useFitLink } from "../../store/fitLinkStore";
import { autoLayout, type LayoutMode } from "../../lib/autoLayout";
import { confirmClobber } from "../../lib/guardClobber";
import { SavedModelsPanel } from "./SavedModelsPanel";

interface ToolbarProps {
  onValidate: () => void;
  onExport: () => void;
  onImport: () => void;
  onShare: () => void;
}

export function Toolbar({ onValidate, onExport, onImport, onShare }: ToolbarProps) {
  const addState = useTopologyStore((s) => s.addState);
  const setPositions = useTopologyStore((s) => s.setPositions);
  const states = useTopologyStore((s) => s.states);
  const transitions = useTopologyStore((s) => s.transitions);
  const undo = useTopologyTemporal((s) => s.undo);
  const redo = useTopologyTemporal((s) => s.redo);
  const canUndo = useTopologyTemporal((s) => s.pastStates.length > 0);
  const canRedo = useTopologyTemporal((s) => s.futureStates.length > 0);

  function tidy(mode: LayoutMode) {
    const st = useTopologyStore.getState();
    if (st.states.length === 0) return;
    setPositions(autoLayout(st.states, mode));
  }

  const overlayMode = useEditorPrefs((s) => s.overlayMode);
  const setOverlayMode = useEditorPrefs((s) => s.setOverlayMode);

  const saved = useSavedTopologies((s) => s.saved);
  const saveModel = useSavedTopologies((s) => s.save);

  const navigate = useNavigate();
  const dataset = useDatasetStore((s) => s.current);
  const setFitLink = useFitLink((s) => s.setFitLink);
  const lastFitJobId = useFitLink((s) => s.lastFitJobId);
  const fitFingerprint = useFitLink((s) => s.fitFingerprint);
  const learnedAvailable =
    !!lastFitJobId && fitFingerprint === topologyFingerprint(states, transitions);
  const [fitting, setFitting] = useState(false);
  const [showModels, setShowModels] = useState(false);

  async function handleFit() {
    if (!dataset || states.length === 0) return;
    setFitting(true);
    try {
      const st = useTopologyStore.getState();
      const result = await startFit({
        topology_yaml: topologyToYAML(st),
        dataset_id: dataset.id,
      });
      setFitLink(result.id, topologyFingerprint(st.states, st.transitions));
      navigate(`/results/${result.id}`);
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert(`Fit failed: ${e instanceof Error ? e.message : "?"}`);
      setFitting(false);
    }
  }

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
    // Loading a saved model replaces the active one — guard the unsaved work
    // (handleSaveCurrent prompts for a name to stash it first).
    const cur = useTopologyStore.getState();
    if (!confirmClobber(cur.states.length, handleSaveCurrent)) return;
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
      <button onClick={() => tidy("left-right")} className={btn} title="Arrange as a left-right chain">
        ⇥ Tidy (chain)
      </button>
      <button onClick={() => tidy("circular")} className={btn} title="Arrange on a circle (ergodic)">
        ◯ Tidy (circle)
      </button>
      <div className="w-px h-6 bg-slate-300" />
      <button
        onClick={handleFit}
        disabled={!dataset || states.length === 0 || fitting}
        title={dataset ? `Fit on ${dataset.filename}` : "Select a dataset on the Data page first"}
        className={btn}
      >
        {fitting ? "Fitting…" : "▶ Fit this topology"}
      </button>
      {dataset ? (
        <span className="text-xs text-slate-400">on {dataset.filename}</span>
      ) : (
        <span className="text-xs text-amber-600">no dataset — pick one on Data</span>
      )}
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={() => undo()} disabled={!canUndo} className={btn} title="Undo (Ctrl+Z)">
        ↶ Undo
      </button>
      <button onClick={() => redo()} disabled={!canRedo} className={btn} title="Redo (Ctrl+Y or Ctrl+Shift+Z)">
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
      <div className="inline-flex rounded border border-slate-300 overflow-hidden text-sm">
        {(["none", "prior", "learned"] as OverlayMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setOverlayMode(m)}
            disabled={m === "learned" && !learnedAvailable}
            className={
              "px-2 py-1 " +
              (overlayMode === m ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-50") +
              (m === "learned" && !learnedAvailable ? " opacity-40 cursor-not-allowed" : "")
            }
            title={
              m === "none" ? "No probabilities"
              : m === "prior" ? "Prior mean (expected P before fit)"
              : learnedAvailable ? "Learned probabilities (after a fit)"
              : "Run ▶ Fit this topology first (and don't change the topology after)"
            }
          >
            {m === "none" ? "—" : m}
          </button>
        ))}
      </div>
      <div className="w-px h-6 bg-slate-300" />
      <button onClick={handleSaveCurrent} className={btn}>💾 Save model</button>
      <div className="relative inline-block">
        <button onClick={() => setShowModels((v) => !v)} className={btn}>
          📂 My models ({Object.keys(saved).length})
        </button>
        {showModels && (
          <SavedModelsPanel
            onLoad={(n) => { handleLoadSaved(n); setShowModels(false); }}
            onClose={() => setShowModels(false)}
          />
        )}
      </div>
    </div>
  );
}
