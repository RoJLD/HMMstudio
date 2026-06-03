import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTopologyStore } from "../store/topologyStore";
import { useDatasetStore } from "../store/datasetStore";
import { yamlToTopology } from "../lib/yaml";
import { confirmClobber } from "../lib/guardClobber";
import { useSavedTopologies } from "../store/savedTopologiesStore";
import { HelpTip } from "../components/help/HelpTip";
import {
  buildTopologyYaml,
  suggestEmission,
  type WizardModel,
  type TransitionShape,
  type WizardEmissionType,
} from "../lib/buildTopologyYaml";

const STEPS = ["Emission", "States", "Transitions", "Training", "Review"] as const;
const SHAPES: { id: TransitionShape; label: string; blurb: string }[] = [
  { id: "ergodic", label: "Ergodic", blurb: "Any state can follow any state (fully connected)." },
  { id: "left-right", label: "Left-right", blurb: "Only stay or advance: sᵢ→sᵢ, sᵢ→sᵢ₊₁. No going back." },
  { id: "bakis", label: "Bakis", blurb: "Left-right plus skip-one: sᵢ→sᵢ₊₂." },
];
const inputCls =
  "border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/40";

const defaultNames = (k: number) => Array.from({ length: k }, (_, i) => `s${i}`);

export default function WizardPage() {
  const navigate = useNavigate();
  const dataset = useDatasetStore((s) => s.current);

  const initial = useMemo<WizardModel>(() => {
    const sug = suggestEmission(dataset);
    return {
      name: "untitled",
      emissionType: sug.type,
      nFeatures: sug.nFeatures,
      covarianceType: "full",
      nMix: 2,
      nSymbols: sug.nSymbols,
      k: 3,
      stateNames: defaultNames(3),
      shape: "ergodic",
      initStrategy: "kmeans",
      seed: 42,
      nIter: 100,
      tol: 1e-4,
      priorAlpha: null,
    };
    // compute once at mount from the dataset present then
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [model, setModel] = useState<WizardModel>(initial);
  const [stepIdx, setStepIdx] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patch = (p: Partial<WizardModel>) => setModel((m) => ({ ...m, ...p }));

  function setK(raw: number) {
    const k = Math.max(1, Number.isFinite(raw) ? raw : 1);
    setModel((m) => {
      const names = m.stateNames.slice(0, k);
      for (let i = names.length; i < k; i++) names.push(`s${i}`);
      return { ...m, k, stateNames: names };
    });
  }

  const hasFeatures =
    model.emissionType === "gaussian" ||
    model.emissionType === "gmm" ||
    model.emissionType === "poisson";

  const mismatch = useMemo<string | null>(() => {
    if (!dataset) return null;
    if (model.emissionType === "multinomial") {
      return dataset.n_cols !== 1
        ? `Dataset has ${dataset.n_cols} columns; multinomial expects a single integer column.`
        : null;
    }
    return model.nFeatures !== dataset.n_cols
      ? `n_features (${model.nFeatures}) ≠ dataset columns (${dataset.n_cols}).`
      : null;
  }, [dataset, model.emissionType, model.nFeatures]);

  function stepValid(idx: number): boolean {
    if (idx === 0) {
      if (model.emissionType === "multinomial") return model.nSymbols >= 2;
      if (model.emissionType === "gmm" && model.nMix < 1) return false;
      return !hasFeatures || model.nFeatures >= 1;
    }
    if (idx === 1) {
      return (
        model.k >= 1 &&
        model.stateNames.every((n) => n.trim() !== "") &&
        new Set(model.stateNames).size === model.stateNames.length
      );
    }
    return true;
  }

  function finish(goToFit: boolean) {
    setError(null);
    try {
      const cur = useTopologyStore.getState();
      const proceed = confirmClobber(cur.states.length, () => {
        const { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha } = cur;
        useSavedTopologies.getState().save({
          name: name || "untitled",
          data: { name, states, transitions, emission, startprob, init, fit, transmat_prior_alpha },
          savedAt: Date.now(),
        });
      });
      if (!proceed) return;
      const partial = yamlToTopology(buildTopologyYaml(model));
      useTopologyStore.getState().loadTopology(partial);
      navigate(goToFit ? "/fit" : "/topology");
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not build topology");
    }
  }

  const isLast = stepIdx === STEPS.length - 1;

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">New guided model</h2>
      <p className="text-slate-600 mb-5">
        Build a topology step by step. On finish it opens in the editor, pre-filled.
      </p>

      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-6 text-xs">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span
              className={
                "w-5 h-5 rounded-full inline-flex items-center justify-center font-semibold " +
                (i === stepIdx
                  ? "bg-brand-600 text-white"
                  : i < stepIdx
                    ? "bg-green-500 text-white"
                    : "bg-slate-200 text-slate-600")
              }
            >
              {i + 1}
            </span>
            <span className={i === stepIdx ? "font-medium text-slate-800" : "text-slate-500"}>
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="text-slate-300">—</span>}
          </li>
        ))}
      </ol>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4 space-y-3">
        {/* ---- Step 1: Emission ---- */}
        {stepIdx === 0 && (
          <>
            {dataset && (
              <p className="text-xs text-slate-500">
                Dataset <span className="font-mono">{dataset.filename}</span> ({dataset.n_cols} cols)
                — suggestion prefilled.
              </p>
            )}
            <label className="flex items-center justify-between gap-2 text-sm">
              <span className="text-slate-700 inline-flex items-center">
                Type
                <HelpTip paramKey="emission.type" />
              </span>
              <select
                value={model.emissionType}
                onChange={(e) => patch({ emissionType: e.target.value as WizardEmissionType })}
                className={inputCls + " w-40"}
              >
                <option value="gaussian">gaussian</option>
                <option value="gmm">gmm</option>
                <option value="multinomial">multinomial</option>
                <option value="poisson">poisson</option>
              </select>
            </label>
            {hasFeatures && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  n_features
                  <HelpTip paramKey="emission.n_features" />
                </span>
                <input
                  type="number"
                  min={1}
                  value={model.nFeatures}
                  onChange={(e) => patch({ nFeatures: parseInt(e.target.value, 10) || 1 })}
                  className={inputCls + " w-40"}
                />
              </label>
            )}
            {(model.emissionType === "gaussian" || model.emissionType === "gmm") && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  covariance
                  <HelpTip paramKey="emission.covariance_type" />
                </span>
                <select
                  value={model.covarianceType}
                  onChange={(e) =>
                    patch({ covarianceType: e.target.value as WizardModel["covarianceType"] })
                  }
                  className={inputCls + " w-40"}
                >
                  <option value="full">full</option>
                  <option value="diag">diag</option>
                  <option value="tied">tied</option>
                  <option value="spherical">spherical</option>
                </select>
              </label>
            )}
            {model.emissionType === "gmm" && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  n_mix
                  <HelpTip paramKey="emission.n_mix" />
                </span>
                <input
                  type="number"
                  min={1}
                  value={model.nMix}
                  onChange={(e) => patch({ nMix: parseInt(e.target.value, 10) || 1 })}
                  className={inputCls + " w-40"}
                />
              </label>
            )}
            {model.emissionType === "multinomial" && (
              <label className="flex items-center justify-between gap-2 text-sm">
                <span className="text-slate-700 inline-flex items-center">
                  n_symbols
                  <HelpTip paramKey="emission.n_symbols" />
                </span>
                <input
                  type="number"
                  min={2}
                  value={model.nSymbols}
                  onChange={(e) => patch({ nSymbols: parseInt(e.target.value, 10) || 2 })}
                  className={inputCls + " w-40"}
                />
              </label>
            )}
            {mismatch && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                ⚠ {mismatch}
              </p>
            )}
          </>
        )}

        {/* ---- Step 2: States ---- */}
        {stepIdx === 1 && (
          <>
            <label className="flex items-center justify-between gap-2 text-sm">
              <span className="text-slate-700 inline-flex items-center">
                Number of states (K)
                <HelpTip paramKey="scan.k_range" />
              </span>
              <input
                type="number"
                min={1}
                value={model.k}
                onChange={(e) => setK(parseInt(e.target.value, 10))}
                className={inputCls + " w-24"}
              />
            </label>
            <p className="text-xs text-slate-500">Optional: rename states (defaults s0…).</p>
            <div className="grid grid-cols-2 gap-2">
              {model.stateNames.map((nm, i) => (
                <input
                  key={i}
                  value={nm}
                  onChange={(e) => {
                    const names = [...model.stateNames];
                    names[i] = e.target.value;
                    patch({ stateNames: names });
                  }}
                  className={inputCls}
                />
              ))}
            </div>
            {!stepValid(1) && (
              <p className="text-xs text-red-700">State names must be non-empty and unique.</p>
            )}
          </>
        )}

        {/* ---- Step 3: Transitions ---- */}
        {stepIdx === 2 && (
          <>
            <span className="text-sm text-slate-700 inline-flex items-center">
              Transition shape
              <HelpTip paramKey="topology.allowed_transitions" />
            </span>
            <div className="space-y-2">
              {SHAPES.map((s) => (
                <label
                  key={s.id}
                  className={
                    "flex items-start gap-2 border rounded p-2 cursor-pointer " +
                    (model.shape === s.id ? "border-brand-400 bg-brand-50" : "border-slate-200")
                  }
                >
                  <input
                    type="radio"
                    name="shape"
                    checked={model.shape === s.id}
                    onChange={() => patch({ shape: s.id })}
                    className="mt-1"
                  />
                  <span>
                    <span className="font-medium text-sm">{s.label}</span>
                    <span className="block text-xs text-slate-500">{s.blurb}</span>
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-slate-500">
              Need a custom structure? Pick Ergodic now and draw the exact edges in the editor.
            </p>
          </>
        )}

        {/* ---- Step 4: Training ---- */}
        {stepIdx === 3 && (
          <>
            <p className="text-sm text-slate-600">
              Sensible defaults are filled in — most users can continue.
            </p>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="text-xs text-brand-700 hover:underline"
            >
              {showAdvanced ? "Hide" : "Show"} advanced training settings
            </button>
            {showAdvanced && (
              <div className="space-y-3 pt-2">
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    init strategy
                    <HelpTip paramKey="init.strategy" />
                  </span>
                  <select
                    value={model.initStrategy}
                    onChange={(e) =>
                      patch({ initStrategy: e.target.value as WizardModel["initStrategy"] })
                    }
                    className={inputCls + " w-40"}
                  >
                    <option value="uniform">uniform</option>
                    <option value="random">random</option>
                    <option value="kmeans">kmeans</option>
                    <option value="data_frequencies">data_frequencies</option>
                  </select>
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    seed
                    <HelpTip paramKey="init.seed" />
                  </span>
                  <input
                    type="number"
                    value={model.seed}
                    onChange={(e) => patch({ seed: parseInt(e.target.value, 10) || 0 })}
                    className={inputCls + " w-40"}
                  />
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    n_iter
                    <HelpTip paramKey="fit.n_iter" />
                  </span>
                  <input
                    type="number"
                    min={1}
                    value={model.nIter}
                    onChange={(e) => patch({ nIter: parseInt(e.target.value, 10) || 1 })}
                    className={inputCls + " w-40"}
                  />
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    tol
                    <HelpTip paramKey="fit.tol" />
                  </span>
                  <input
                    type="number"
                    step={1e-5}
                    value={model.tol}
                    onChange={(e) => patch({ tol: parseFloat(e.target.value) || 1e-4 })}
                    className={inputCls + " w-40"}
                  />
                </label>
                <label className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 inline-flex items-center">
                    α (Dirichlet)
                    <HelpTip paramKey="priors.alpha" />
                  </span>
                  <input
                    type="number"
                    step={0.1}
                    min={0}
                    value={model.priorAlpha ?? ""}
                    placeholder="(MLE)"
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      patch({ priorAlpha: Number.isFinite(v) ? v : null });
                    }}
                    className={inputCls + " w-40"}
                  />
                </label>
              </div>
            )}
          </>
        )}

        {/* ---- Step 5: Review ---- */}
        {stepIdx === 4 && (
          <>
            <p className="text-sm text-slate-700">
              <strong>
                {model.k}-state {model.emissionType}
              </strong>{" "}
              model, <span className="font-mono">{model.shape}</span> transitions,{" "}
              <span className="font-mono">{model.initStrategy}</span> init.
            </p>
            <pre className="text-xs bg-slate-50 border border-slate-200 rounded p-3 overflow-x-auto whitespace-pre-wrap">
              {buildTopologyYaml(model)}
            </pre>
          </>
        )}
      </div>

      {error && (
        <p className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={stepIdx === 0}
          onClick={() => setStepIdx((i) => Math.max(0, i - 1))}
          className={
            "px-4 py-2 rounded text-sm font-medium " +
            (stepIdx === 0
              ? "bg-slate-100 text-slate-400 cursor-not-allowed"
              : "bg-slate-200 text-slate-700 hover:bg-slate-300")
          }
        >
          Back
        </button>

        {!isLast ? (
          <button
            type="button"
            disabled={!stepValid(stepIdx)}
            onClick={() => setStepIdx((i) => Math.min(STEPS.length - 1, i + 1))}
            className={
              "px-4 py-2 rounded text-sm font-medium " +
              (stepValid(stepIdx)
                ? "bg-brand-600 text-white hover:bg-brand-700"
                : "bg-slate-200 text-slate-500 cursor-not-allowed")
            }
          >
            Next
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => finish(false)}
              className="px-4 py-2 rounded text-sm font-medium bg-brand-600 text-white hover:bg-brand-700"
            >
              Finish → open in editor
            </button>
            {dataset && (
              <button
                type="button"
                onClick={() => finish(true)}
                className="px-4 py-2 rounded text-sm font-medium bg-slate-200 text-slate-700 hover:bg-slate-300"
              >
                Finish & go to Fit
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
