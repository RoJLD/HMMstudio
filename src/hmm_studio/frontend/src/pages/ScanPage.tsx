import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getScan, type ScanResult } from "../api/client";
import { BicScatter } from "../components/results/BicScatter";

export default function ScanPage() {
  const { parentId } = useParams<{ parentId: string }>();
  const [scan, setScan] = useState<ScanResult | null>(null);

  useEffect(() => {
    if (!parentId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await getScan(parentId);
        if (!cancelled) setScan(r);
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

  if (!scan) {
    return (
      <div className="text-slate-600">
        Loading scan <code>{parentId}</code>...
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">
        K-scan{" "}
        <span className="text-sm font-mono text-slate-500">{scan.parent_id}</span>
      </h2>
      <p className="text-slate-600 mb-4">
        Status: <Badge status={scan.overall_status} />
        {scan.best_k_by_bic !== null && (
          <span className="ml-3 text-sm">
            Best by BIC:{" "}
            <strong className="font-mono">K={scan.best_k_by_bic}</strong>
          </span>
        )}
        {scan.best_k_by_aic !== null && (
          <span className="ml-3 text-sm">
            Best by AIC:{" "}
            <strong className="font-mono">K={scan.best_k_by_aic}</strong>
          </span>
        )}
      </p>

      <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">BIC / AIC vs K</h3>
        <BicScatter
          data={scan.children
            .filter((c) => c.bic !== null && c.aic !== null)
            .map((c) => ({ k: c.k, bic: c.bic!, aic: c.aic! }))}
          bestBic={scan.best_k_by_bic}
        />
      </div>

      <div className="border border-slate-200 rounded-md bg-white overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-slate-700">K</th>
              <th className="text-left px-3 py-2 font-medium text-slate-700">Status</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">log-lik</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">BIC</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">AIC</th>
              <th className="text-right px-3 py-2 font-medium text-slate-700">iters</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {scan.children.map((c) => (
              <tr key={c.job_id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono font-semibold">{c.k}</td>
                <td className="px-3 py-2">
                  <Badge status={c.status} />
                </td>
                <td className="px-3 py-2 text-right font-mono">
                  {fmt(c.log_likelihood)}
                </td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.k === scan.best_k_by_bic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.bic)}
                </td>
                <td
                  className={
                    "px-3 py-2 text-right font-mono " +
                    (c.k === scan.best_k_by_aic ? "text-green-700 font-bold" : "")
                  }
                >
                  {fmt(c.aic)}
                </td>
                <td className="px-3 py-2 text-right font-mono">
                  {c.n_iter_actual ?? "—"}
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
