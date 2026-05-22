import { useCallback, useEffect, useRef, useState } from "react";
import {
  listWarehouse,
  refreshWarehouse,
  uploadToWarehouse,
  type WarehouseEntry,
  type WarehouseList,
} from "../../api/client";
import { FormatBadge } from "./FormatBadge";

interface Props {
  /** Notifies the parent of the warehouse status so it can decide layout. */
  onListLoaded?: (list: WarehouseList) => void;
  /** Currently selected rel_path; used for visual highlight. */
  selectedRelPath: string | null;
  /** Called when the user clicks a warehouse entry. */
  onSelect: (relPath: string) => void;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return iso;
  const deltaSec = Math.floor((Date.now() - t) / 1000);
  if (deltaSec < 60) return `${deltaSec}s ago`;
  if (deltaSec < 3600) return `${Math.floor(deltaSec / 60)}m ago`;
  if (deltaSec < 86400) return `${Math.floor(deltaSec / 3600)}h ago`;
  if (deltaSec < 86400 * 30) return `${Math.floor(deltaSec / 86400)}d ago`;
  return new Date(iso).toISOString().slice(0, 10);
}

interface Grouped {
  [parent: string]: WarehouseEntry[];
}

function groupByParent(entries: WarehouseEntry[]): Grouped {
  const out: Grouped = {};
  for (const e of entries) {
    const idx = e.rel_path.lastIndexOf("/");
    const parent = idx === -1 ? "" : e.rel_path.slice(0, idx);
    if (!out[parent]) out[parent] = [];
    out[parent].push(e);
  }
  return out;
}

export function WarehouseSidebar({
  onListLoaded,
  selectedRelPath,
  onSelect,
}: Props) {
  const [list, setList] = useState<WarehouseList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingWh, setUploadingWh] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [copied, setCopied] = useState(false);

  const reload = useCallback(
    async (forceRescan = false) => {
      setLoading(true);
      setError(null);
      try {
        const data = forceRescan
          ? await refreshWarehouse()
          : await listWarehouse();
        setList(data);
        onListLoaded?.(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "failed to load warehouse");
      } finally {
        setLoading(false);
      }
    },
    [onListLoaded],
  );

  useEffect(() => {
    void reload(false);
  }, [reload]);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploadingWh(true);
      setError(null);
      try {
        await uploadToWarehouse(file);
        await reload(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "upload failed");
      } finally {
        setUploadingWh(false);
      }
    },
    [reload],
  );

  const copyPath = useCallback(async () => {
    if (!list?.warehouse_path) return;
    try {
      await navigator.clipboard.writeText(list.warehouse_path);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard may be unavailable (insecure context) — silently ignore
    }
  }, [list]);

  // Empty state: no warehouse configured at all.
  if (list && list.warehouse_path === "") {
    return (
      <div className="border border-slate-200 rounded-md bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">
          Data warehouse
        </h3>
        <p className="text-xs text-slate-600 mb-2">
          No warehouse configured.
        </p>
        <p className="text-xs text-slate-500">
          Set <code className="font-mono bg-slate-100 px-1 rounded">HMM_STUDIO_WAREHOUSE_PATH</code>{" "}
          and restart the server.
        </p>
      </div>
    );
  }

  const grouped = list ? groupByParent(list.entries) : {};
  const parents = Object.keys(grouped).sort();

  return (
    <div className="border border-slate-200 rounded-md bg-white p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-700">Warehouse</h3>
        <button
          type="button"
          onClick={() => void reload(true)}
          disabled={loading}
          className="text-xs px-2 py-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "..." : "Refresh"}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
          {error}
        </p>
      )}

      {list && list.entries.length === 0 && !loading && (
        <p className="text-xs text-slate-500">
          No supported datasets found in{" "}
          <code className="font-mono bg-slate-100 px-1 rounded break-all">
            {list.warehouse_path}
          </code>
          .
        </p>
      )}

      {list && list.entries.length > 0 && (
        <ul className="divide-y divide-slate-100 -mx-2">
          {parents.map((parent) => (
            <li key={parent || "__root__"} className="py-1">
              {parent && (
                <div className="px-2 py-1 text-xs font-mono text-slate-500 uppercase tracking-wide">
                  {parent}/
                </div>
              )}
              <ul>
                {grouped[parent].map((e) => {
                  const isSelected = selectedRelPath === e.rel_path;
                  const filename = e.rel_path.split("/").pop() ?? e.rel_path;
                  return (
                    <li key={e.rel_path}>
                      <button
                        type="button"
                        onClick={() => onSelect(e.rel_path)}
                        className={
                          "w-full text-left px-2 py-1.5 rounded text-xs flex items-center gap-2 transition-colors " +
                          (isSelected
                            ? "bg-brand-50 text-brand-900"
                            : "hover:bg-slate-50 text-slate-800")
                        }
                        title={e.rel_path}
                      >
                        <FormatBadge format={e.format} />
                        <span className="font-medium truncate flex-1">
                          {filename}
                        </span>
                        {e.has_sidecar && (
                          <span
                            className="text-amber-500"
                            title="Has sidecar metadata"
                          >
                            ★
                          </span>
                        )}
                        <span className="text-slate-400 shrink-0">
                          {formatBytes(e.size_bytes)}
                        </span>
                        <span className="text-slate-400 shrink-0">
                          {relativeTime(e.modified_at)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ul>
      )}

      <div className="border-t border-slate-100 pt-3">
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.parquet,.feather,.json,.jsonl,.xlsx,.xls"
          style={{ display: "none" }}
          onChange={(ev) => {
            const f = ev.target.files?.[0];
            if (f) void handleUpload(f);
            ev.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploadingWh}
          className="w-full text-xs px-2 py-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
        >
          {uploadingWh ? "Uploading..." : "Upload to warehouse"}
        </button>
      </div>

      {/* TODO(spec § 7 done-list "Settings UI exposée"): replace this footer
          with a proper Settings page allowing live edit of warehouse_path.
          For now we surface the configured path (read-only). */}
      {list && list.warehouse_path && (
        <div className="border-t border-slate-100 pt-2 text-[10px] text-slate-500">
          <div className="flex items-center justify-between gap-2">
            <code
              className="font-mono break-all flex-1"
              title={list.warehouse_path}
            >
              {list.warehouse_path}
            </code>
            <button
              type="button"
              onClick={() => void copyPath()}
              className="shrink-0 px-1.5 py-0.5 rounded border border-slate-200 hover:bg-slate-50"
            >
              {copied ? "✓" : "Copy"}
            </button>
          </div>
          <p className="mt-1 text-slate-400">
            Configured via{" "}
            <code className="font-mono">HMM_STUDIO_WAREHOUSE_PATH</code>.
            Restart the server to change.
          </p>
        </div>
      )}
    </div>
  );
}
