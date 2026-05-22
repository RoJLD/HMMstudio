import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTopologyStore } from "../store/topologyStore";
import { useDatasetStore } from "../store/datasetStore";
import { topologyToYAML } from "../lib/yaml";
import { startFit } from "../api/client";

export default function FitPage() {
  const dataset = useDatasetStore((s) => s.current);
  const states = useTopologyStore((s) => s.states);
  const navigate = useNavigate();

  const [seed, setSeed] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = !!dataset && states.length > 0 && !submitting;

  async function handleSubmit() {
    if (!dataset) return;
    setError(null);
    setSubmitting(true);
    try {
      const yamlText = topologyToYAML(useTopologyStore.getState());
      const result = await startFit({
        topology_yaml: yamlText,
        dataset_id: dataset.id,
        seed: seed === "" ? undefined : Number(seed),
      });
      navigate(`/results/${result.id}`);
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
        {submitting ? "Submitting…" : "Launch fit"}
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
