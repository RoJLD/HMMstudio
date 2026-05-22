import { useState } from "react";
import { getHealth } from "../api/client";

export default function HomePage() {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function checkHealth() {
    setStatus(null);
    setError(null);
    try {
      const res = await getHealth();
      setStatus(res.status);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "unknown error");
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">
        Welcome to hmm-studio
      </h2>
      <p className="text-slate-600 mb-6">
        Web UI for the hmm-core engine. Backend skeleton (B.1) and
        WebSocket streaming (B.2) are live. The topology editor (B.4),
        data upload UI (B.5) and results view (B.6) are next.
      </p>
      <div className="border border-slate-200 rounded-md p-4 bg-white">
        <h3 className="font-semibold text-slate-900 mb-2">
          Backend health check
        </h3>
        <button
          onClick={checkHealth}
          className="px-4 py-2 bg-brand-600 text-white rounded hover:bg-brand-700 text-sm"
        >
          GET /health
        </button>
        {status && (
          <p className="mt-3 text-green-700 text-sm">
            Backend says: <code className="bg-slate-100 px-1">{status}</code>
          </p>
        )}
        {error && (
          <p className="mt-3 text-red-700 text-sm">Error: {error}</p>
        )}
      </div>
    </div>
  );
}
