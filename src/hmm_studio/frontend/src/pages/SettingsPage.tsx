import { useCallback, useEffect, useState } from "react";
import { getSettings, updateSettings, type Settings } from "../api/client";

function sourceLabel(s: Settings): string {
  switch (s.warehouse_path_source) {
    case "db":
      return "from database (overrides environment)";
    case "env":
      return "from environment variable HMM_STUDIO_WAREHOUSE_PATH";
    case "unset":
    default:
      return "not configured";
  }
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Re-sync the text input to whatever value the server reports. We show the
  // resolved value when source is "db" (so editing starts from the current
  // override); for "env"/"unset" we leave the input empty so the user can
  // type a fresh DB override without accidentally re-saving the env value.
  const syncFromServer = useCallback((s: Settings) => {
    setSettings(s);
    setInput(s.warehouse_path_source === "db" ? (s.warehouse_path ?? "") : "");
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getSettings()
      .then((s) => {
        if (cancelled) return;
        syncFromServer(s);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "failed to load settings");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [syncFromServer]);

  function flashSuccess(msg: string) {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 3000);
  }

  async function handleSave() {
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const next = await updateSettings({
        warehouse_path: input.trim() === "" ? null : input.trim(),
      });
      syncFromServer(next);
      flashSuccess("Saved.");
    } catch (e) {
      // Backend returns 400 with body like {"detail": "..."}; surface that.
      const raw = e instanceof Error ? e.message : "save failed";
      const match = raw.match(/HTTP \d+: (.+)$/);
      let msg = raw;
      if (match) {
        try {
          const body = JSON.parse(match[1]);
          if (body && typeof body.detail === "string") msg = body.detail;
        } catch {
          msg = match[1];
        }
      }
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const next = await updateSettings({ warehouse_path: null });
      syncFromServer(next);
      setInput("");
      flashSuccess("Cleared. Using environment default (if any).");
    } catch (e) {
      setError(e instanceof Error ? e.message : "reset failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
        Settings
      </h2>
      <p className="text-slate-600 dark:text-slate-400 mb-6">
        Configure user-level preferences. Settings are stored in the studio's
        local SQLite database and take effect immediately (no server restart
        needed).
      </p>

      {loading && (
        <p className="text-sm text-slate-500">Loading current settings…</p>
      )}

      {!loading && settings && (
        <section className="border border-slate-200 dark:border-slate-700 rounded-md p-5 bg-white dark:bg-slate-800">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
            Data warehouse
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Currently {sourceLabel(settings)}.
            {settings.warehouse_path_source !== "unset" && settings.warehouse_path && (
              <>
                {" "}
                Resolved path:{" "}
                <code className="font-mono text-slate-700 dark:text-slate-300">
                  {settings.warehouse_path}
                </code>
              </>
            )}
          </p>

          <label
            htmlFor="warehouse_path"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
          >
            Warehouse path
          </label>
          <input
            id="warehouse_path"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="/absolute/path/to/your/data"
            spellCheck={false}
            autoComplete="off"
            className="block w-full font-mono text-sm rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Must be an absolute path to an existing directory. Leave empty to
            fall back to the environment default.
          </p>

          {settings.warehouse_path_env && (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Environment default (HMM_STUDIO_WAREHOUSE_PATH):{" "}
              <code className="font-mono text-slate-700 dark:text-slate-300">
                {settings.warehouse_path_env}
              </code>
            </p>
          )}

          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-brand-600 text-white rounded hover:bg-brand-700 text-sm disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={handleReset}
              disabled={saving || settings.warehouse_path_source !== "db"}
              className="px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-sm disabled:opacity-60"
              title={
                settings.warehouse_path_source === "db"
                  ? "Clear the database override and fall back to the environment default"
                  : "No database override to clear"
              }
            >
              Reset to environment default
            </button>
          </div>

          {success && (
            <p className="mt-3 text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
              {success}
            </p>
          )}

          {error && (
            <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </p>
          )}

          <hr className="my-5 border-slate-200 dark:border-slate-700" />

          <div className="text-xs text-slate-500 dark:text-slate-400 space-y-2">
            <p>
              <strong>What is a warehouse?</strong> A directory on your machine
              containing supported dataset files (CSV, Parquet, JSON/JSONL,
              Excel, Feather, TSV). hmm-studio scans it recursively and lets
              you browse, preview, annotate, and promote datasets to a fit.
            </p>
            <p>
              Sidecar metadata is stored next to each file as{" "}
              <code className="font-mono">&lt;filename&gt;.hmm.yaml</code>.
              See the Phase B.10 spec
              (<code className="font-mono">
                docs/specs/2026-05-22-phase-b10-data-warehouse.md
              </code>) for details.
            </p>
          </div>
        </section>
      )}

      {!loading && !settings && error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}
    </div>
  );
}
