import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTopologyStore } from "../store/topologyStore";
import { useDatasetStore } from "../store/datasetStore";
import { topologyToYAML } from "../lib/yaml";
import { startFit, startScan } from "../api/client";

export default function FitPage() {
  const dataset = useDatasetStore((s) => s.current);
  const states = useTopologyStore((s) => s.states);
  const navigate = useNavigate();

  const [seed, setSeed] = useState<number | "">("");
  const [covariateNames, setCovariateNames] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanMode, setScanMode] = useState(false);
  const [kMin, setKMin] = useState(2);
  const [kMax, setKMax] = useState(6);

  const canSubmit = !!dataset && states.length > 0 && !submitting;

  async function handleSubmit() {
    if (!dataset) return;
    setError(null);
    setSubmitting(true);
    try {
      const yamlText = topologyToYAML(useTopologyStore.getState());
      if (scanMode) {
        const r = await startScan({
          topology_yaml: yamlText,
          dataset_id: dataset.id,
          k_min: kMin,
          k_max: kMax,
          seed: seed === "" ? undefined : Number(seed),
          covariate_names: covariateNames.length > 0 ? covariateNames : undefined,
        });
        navigate(`/scan/${r.parent_id}`);
      } else {
        const result = await startFit({
          topology_yaml: yamlText,
          dataset_id: dataset.id,
          seed: seed === "" ? undefined : Number(seed),
          covariate_names: covariateNames.length > 0 ? covariateNames : undefined,
        });
        navigate(`/results/${result.id}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "fit failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">Fit</h2>
      <p className="text-slate-600 mb-6">
        Launch a Baum-Welch fit using the current topology and the most recently
        uploaded dataset.
      </p>

      <div className="space-y-4 mb-6">
        <Status label="Topology" ok={states.length > 0}>
          {states.length > 0
            ? `${states.length} states, ${useTopologyStore.getState().transitions.length} transitions`
            : "no topology — go to the Topology editor first"}
        </Status>
        <Status label="Dataset" ok={!!dataset}>
          {dataset
            ? `${dataset.filename} (${dataset.n_rows} × ${dataset.n_cols})`
            : "no dataset — upload one on the Data page"}
        </Status>
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <label className="flex items-center gap-3 text-sm">
          <span className="text-slate-700 w-24">Seed (override)</span>
          <input
            type="number"
            value={seed}
            onChange={(e) =>
              setSeed(e.target.value === "" ? "" : parseInt(e.target.value, 10))
            }
            placeholder="(use topology default)"
            className="border border-slate-300 rounded px-2 py-1 text-sm flex-1"
          />
        </label>
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-3">
          <input
            type="checkbox"
            checked={scanMode}
            onChange={(e) => setScanMode(e.target.checked)}
          />
          K-scan mode (fit one model per K in range)
        </label>
        {scanMode && (
          <div className="flex items-center gap-3 text-sm">
            <label className="flex items-center gap-2">
              <span className="text-slate-600">k_min</span>
              <input
                type="number"
                min={1}
                value={kMin}
                onChange={(e) => setKMin(parseInt(e.target.value, 10) || 1)}
                className="border border-slate-300 rounded px-2 py-1 w-16"
              />
            </label>
            <label className="flex items-center gap-2">
              <span className="text-slate-600">k_max</span>
              <input
                type="number"
                min={kMin}
                value={kMax}
                onChange={(e) => setKMax(parseInt(e.target.value, 10) || 1)}
                className="border border-slate-300 rounded px-2 py-1 w-16"
              />
            </label>
            <span className="text-xs text-slate-500">
              {Math.max(0, kMax - kMin + 1)} fits will run in parallel
            </span>
          </div>
        )}
      </div>

      {dataset && dataset.columns.length > 1 && (
        <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-2">
            Covariates (optional — enables NHMM)
          </h3>
          <p className="text-xs text-slate-500 mb-2">
            Mark columns that should drive time-varying transitions. Unmarked
            columns are observation features.
          </p>
          <div className="flex flex-wrap gap-2">
            {dataset.columns.map((c) => (
              <label
                key={c}
                className="flex items-center gap-1.5 text-xs px-2 py-1 border border-slate-200 rounded cursor-pointer hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={covariateNames.includes(c)}
                  onChange={(e) => {
                    setCovariateNames(
                      e.target.checked
                        ? [...covariateNames, c]
                        : covariateNames.filter((x) => x !== c),
                    );
                  }}
                />
                <span className="font-mono">{c}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={handleSubmit}
        className={
          "px-4 py-2 rounded text-sm font-medium " +
          (canSubmit
            ? "bg-brand-600 text-white hover:bg-brand-700"
            : "bg-slate-200 text-slate-500 cursor-not-allowed")
        }
      >
        {submitting ? "Submitting…" : scanMode ? "Launch K-scan" : "Launch fit"}
      </button>

      {error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}
    </div>
  );
}

function Status({
  label,
  ok,
  children,
}: {
  label: string;
  ok: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-3 text-sm">
      <span
        className={
          "inline-block w-5 h-5 rounded-full text-center leading-5 text-xs font-bold " +
          (ok ? "bg-green-500 text-white" : "bg-slate-300 text-slate-600")
        }
      >
        {ok ? "✓" : "?"}
      </span>
      <span className="text-slate-700 font-medium w-24">{label}</span>
      <span className="text-slate-600">{children}</span>
    </div>
  );
}
