import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTopologyStore } from "../store/topologyStore";
import { useDatasetStore } from "../store/datasetStore";
import { topologyToYAML } from "../lib/yaml";
import {
  startCompare,
  getCompare,
  type CompareResult,
} from "../api/client";
import { HelpTip } from "../components/help/HelpTip";

const EMISSION_CHOICES = ["gaussian", "gmm", "poisson"] as const;

export default function ComparePage() {
  const { parentId } = useParams<{ parentId: string }>();
  return parentId ? <CompareResults parentId={parentId} /> : <CompareForm />;
}

function CompareForm() {
  const dataset = useDatasetStore((s) => s.current);
  const states = useTopologyStore((s) => s.states);
  const navigate = useNavigate();

  const [emissions, setEmissions] = useState<string[]>(["gaussian"]);
  const [nMix, setNMix] = useState(2);
  const [kMin, setKMin] = useState(2);
  const [kMax, setKMax] = useState(5);
  const [seed, setSeed] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nCells = emissions.length * Math.max(0, kMax - kMin + 1);
  const canSubmit =
    !!dataset && states.length > 0 && emissions.length > 0 && kMax >= kMin && !submitting;

  function toggleEmission(e: string, on: boolean) {
    setEmissions((cur) => (on ? [...cur, e] : cur.filter((x) => x !== e)));
  }

  async function handleLaunch() {
    if (!dataset) return;
    setError(null);
    setSubmitting(true);
    try {
      const yamlText = topologyToYAML(useTopologyStore.getState());
      const r = await startCompare({
        topology_yaml: yamlText,
        dataset_id: dataset.id,
        k_min: kMin,
        k_max: kMax,
        emission_types: emissions,
        n_mix: nMix,
        seed: seed === "" ? undefined : Number(seed),
      });
      navigate(`/compare/${r.parent_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "compare failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">Compare models</h2>
      <p className="text-slate-600 mb-6">
        Fit a grid of comparable emission families × K on the current dataset and
        rank them by BIC / AIC / HQIC. All candidates model{" "}
        <span className="font-mono">P(X)</span>, so the information criteria are
        directly comparable.
      </p>

      <div className="space-y-4 mb-6">
        <Status label="Topology" ok={states.length > 0}>
          {states.length > 0
            ? `${states.length} states (used as the base; emission + K are swept)`
            : "no topology — go to the Topology editor first"}
        </Status>
        <Status label="Dataset" ok={!!dataset}>
          {dataset
            ? `${dataset.filename} (${dataset.n_rows} × ${dataset.n_cols})`
            : "no dataset — upload one on the Data page"}
        </Status>
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2 inline-flex items-center">
          Emission families
          <HelpTip paramKey="compare.emission_types" />
        </h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {EMISSION_CHOICES.map((e) => (
            <label
              key={e}
              className="flex items-center gap-1.5 text-sm px-2 py-1 border border-slate-200 rounded cursor-pointer hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={emissions.includes(e)}
                onChange={(ev) => toggleEmission(e, ev.target.checked)}
              />
              <span className="font-mono">{e}</span>
            </label>
          ))}
        </div>
        {emissions.includes("gmm") && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-slate-600 inline-flex items-center">
              n_mix (GMM)
              <HelpTip paramKey="emission.n_mix" />
            </span>
            <input
              type="number"
              min={2}
              value={nMix}
              onChange={(e) => setNMix(parseInt(e.target.value, 10) || 2)}
              className="border border-slate-300 rounded px-2 py-1 w-16"
            />
          </label>
        )}
        {emissions.includes("poisson") && (
          <p className="text-xs text-amber-700 mt-2">
            Poisson expects integer count data; on continuous data those
            candidates will be reported as failed.
          </p>
        )}
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-slate-600 inline-flex items-center">
              k_min
              <HelpTip paramKey="scan.k_range" />
            </span>
            <input
              type="number"
              min={1}
              value={kMin}
              onChange={(e) => setKMin(parseInt(e.target.value, 10) || 1)}
              className="border border-slate-300 rounded px-2 py-1 w-16"
            />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-slate-600 inline-flex items-center">
              k_max
              <HelpTip paramKey="scan.k_range" />
            </span>
            <input
              type="number"
              min={kMin}
              value={kMax}
              onChange={(e) => setKMax(parseInt(e.target.value, 10) || 1)}
              className="border border-slate-300 rounded px-2 py-1 w-16"
            />
          </label>
          <span className="text-xs text-slate-500">{nCells} fits will run in parallel</span>
        </div>
      </div>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-4">
        <label className="flex items-center gap-3 text-sm">
          <span className="text-slate-700 w-24 inline-flex items-center">
            Seed (override)
            <HelpTip paramKey="init.seed" />
          </span>
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(e.target.value === "" ? "" : parseInt(e.target.value, 10))}
            placeholder="(use topology default)"
            className="border border-slate-300 rounded px-2 py-1 text-sm flex-1"
          />
        </label>
      </div>

      <button
        type="button"
        disabled={!canSubmit}
        onClick={handleLaunch}
        className={
          "px-4 py-2 rounded text-sm font-medium " +
          (canSubmit
            ? "bg-brand-600 text-white hover:bg-brand-700"
            : "bg-slate-200 text-slate-500 cursor-not-allowed")
        }
      >
        {submitting ? "Submitting…" : "Launch comparison"}
      </button>

      {error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <p className="mt-4 text-xs text-slate-500">
        NHMM / Factorial variants are not offered here — they need explicit
        covariates / chain specs. Use the Python API (
        <span className="font-mono">hmm_core.compare_models</span>) or{" "}
        <span className="font-mono">hmm-fit compare</span> for those.
      </p>
    </div>
  );
}

function CompareResults({ parentId }: { parentId: string }) {
  const [cmp, setCmp] = useState<CompareResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await getCompare(parentId);
        if (!cancelled) setCmp(r);
        if (r.overall_status === "running" || r.overall_status === "queued") {
          setTimeout(poll, 500);
        }
      } catch {
        // ignore transient errors
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [parentId]);

  if (!cmp) {
    return (
      <div className="text-slate-600">
        Loading comparison <code>{parentId}</code>...
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">
        Model comparison{" "}
        <span className="text-sm font-mono text-slate-500">{cmp.parent_id}</span>
      </h2>
      <p className="text-slate-600 mb-4">
        Status: <Badge status={cmp.overall_status} />
        {cmp.best_label_by_bic && (
          <span className="ml-3 text-sm">
            Best by BIC: <strong className="font-mono">{cmp.best_label_by_bic}</strong>
          </span>
        )}
        {cmp.best_label_by_aic && (
          <span className="ml-3 text-sm">
            Best by AIC: <strong className="font-mono">{cmp.best_label_by_aic}</strong>
          </span>
        )}
        {cmp.best_label_by_hqic && (
          <span className="ml-3 text-sm">
            Best by HQIC: <strong className="font-mono">{cmp.best_label_by_hqic}</strong>
          </span>
        )}
      </p>

      <div className="border border-slate-200 rounded-md bg-white overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-slate-700">candidate</th>
              <th className="text-left px-3 py-2 font-medium text-slate-700">emission</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">K</th>
              <th className="text-left px-3 py-2 font-medium text-slate-700">Status</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">log-lik</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">BIC</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">AIC</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">HQIC</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {cmp.children.map((c) => (
              <tr key={c.job_id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono font-semibold">{c.label}</td>
                <td className="px-3 py-2 font-mono">{c.emission}</td>
                <td className="px-3 py-2 text-right font-mono">{c.k}</td>
                <td className="px-3 py-2">
                  <Badge status={c.status} />
                </td>
                <td className="px-3 py-2 text-right font-mono">{fmt(c.log_likelihood)}</td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.label === cmp.best_label_by_bic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.bic)}
                </td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.label === cmp.best_label_by_aic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.aic)}
                </td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.label === cmp.best_label_by_hqic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.hqic)}
                </td>
                <td className="px-3 py-2 text-right">
                  {c.status === "done" && (
                    <Link
                      to={`/results/${c.job_id}`}
                      className="text-indigo-600 hover:underline text-xs"
                    >
                      view →
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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

function Badge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-slate-200 text-slate-800",
    running: "bg-blue-100 text-blue-800",
    done: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    cancelled: "bg-amber-100 text-amber-800",
  };
  return (
    <span
      className={
        "inline-block px-2 py-0.5 rounded text-xs font-medium " +
        (colors[status] ?? "bg-slate-200 text-slate-800")
      }
    >
      {status}
    </span>
  );
}

function fmt(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return v.toFixed(2);
}
