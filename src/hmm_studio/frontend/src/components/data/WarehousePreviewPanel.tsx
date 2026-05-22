import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getWarehouseMeta,
  getWarehousePreview,
  promoteWarehouseDataset,
  putWarehouseMeta,
  type DatasetPreview,
  type WarehousePreview,
  type WarehouseSidecarMeta,
} from "../../api/client";
import { useDatasetStore } from "../../store/datasetStore";
import { DatasetPreviewCard } from "./DatasetPreviewCard";

interface Props {
  relPath: string;
}

/** Adapt a WarehousePreview to the DatasetPreview shape used by
 * DatasetPreviewCard so we don't duplicate table-rendering code.
 * The `id` field is a synthetic marker (the rel_path) — this preview
 * is NOT a real Dataset row yet; promotion happens on "Use for fit". */
function adaptToDatasetPreview(p: WarehousePreview): DatasetPreview {
  return {
    id: `warehouse:${p.rel_path}`,
    filename: p.rel_path,
    n_rows: p.n_rows_total,
    n_cols: p.n_cols,
    columns: p.columns,
    dtypes: p.dtypes,
    head: p.head,
  };
}

export function WarehousePreviewPanel({ relPath }: Props) {
  const navigate = useNavigate();
  const setCurrent = useDatasetStore((s) => s.setCurrent);
  const addToHistory = useDatasetStore((s) => s.addToHistory);

  const [preview, setPreview] = useState<WarehousePreview | null>(null);
  const [meta, setMeta] = useState<WarehouseSidecarMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [promoting, setPromoting] = useState(false);

  // Edit form fields (kept simple: textareas, no fancy yaml editor).
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editColumnsJson, setEditColumnsJson] = useState("");
  const [editColumnsErr, setEditColumnsErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, m] = await Promise.all([
        getWarehousePreview(relPath, 10),
        getWarehouseMeta(relPath),
      ]);
      setPreview(p);
      setMeta(m.sidecar);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load warehouse file");
    } finally {
      setLoading(false);
    }
  }, [relPath]);

  useEffect(() => {
    setEditing(false);
    void reload();
  }, [reload]);

  const startEdit = useCallback(() => {
    setEditName(meta?.name ?? "");
    setEditDescription(meta?.description ?? "");
    setEditNotes(meta?.notes ?? "");
    setEditColumnsJson(
      meta?.columns ? JSON.stringify(meta.columns, null, 2) : "[]",
    );
    setEditColumnsErr(null);
    setEditing(true);
  }, [meta]);

  const saveEdit = useCallback(async () => {
    let columns: Array<Record<string, unknown>> | undefined;
    if (editColumnsJson.trim()) {
      try {
        const parsed = JSON.parse(editColumnsJson) as unknown;
        if (!Array.isArray(parsed)) {
          throw new Error("columns must be a JSON array");
        }
        columns = parsed as Array<Record<string, unknown>>;
      } catch (e) {
        setEditColumnsErr(e instanceof Error ? e.message : "invalid JSON");
        return;
      }
    }
    setSaving(true);
    setError(null);
    try {
      const payload: WarehouseSidecarMeta = {
        schema_version: meta?.schema_version ?? 1,
        name: editName || undefined,
        description: editDescription || undefined,
        notes: editNotes || undefined,
        columns,
        provenance: meta?.provenance,
        extra: meta?.extra,
      };
      await putWarehouseMeta(relPath, payload);
      setEditing(false);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "save failed");
    } finally {
      setSaving(false);
    }
  }, [editName, editDescription, editNotes, editColumnsJson, meta, relPath, reload]);

  const useForFit = useCallback(async () => {
    setPromoting(true);
    setError(null);
    try {
      const ds = await promoteWarehouseDataset(relPath);
      setCurrent(ds);
      addToHistory(ds);
      navigate("/fit");
    } catch (e) {
      setError(e instanceof Error ? e.message : "promote failed");
    } finally {
      setPromoting(false);
    }
  }, [relPath, setCurrent, addToHistory, navigate]);

  if (loading && !preview) {
    return (
      <div className="border border-slate-200 rounded-md bg-white p-4 text-sm text-slate-600">
        Loading {relPath}...
      </div>
    );
  }

  if (error && !preview) {
    return (
      <div className="border border-red-200 rounded-md bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!preview) return null;

  return (
    <div className="flex flex-col gap-4">
      <DatasetPreviewCard preview={adaptToDatasetPreview(preview)} />

      <div className="border border-slate-200 rounded-md bg-white p-4">
        <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
          <h3 className="text-sm font-semibold text-slate-700">
            Sidecar metadata
          </h3>
          {!editing && (
            <button
              type="button"
              onClick={startEdit}
              className="text-xs px-2 py-1 rounded border border-slate-200 hover:bg-slate-50"
            >
              Edit sidecar
            </button>
          )}
        </div>

        {!editing && !meta && (
          <p className="text-xs text-slate-500">
            No sidecar yet. Click <em>Edit sidecar</em> to add notes,
            description, and column roles.
          </p>
        )}

        {!editing && meta && (
          <div className="text-xs text-slate-700 space-y-2">
            {meta.name && (
              <div>
                <span className="text-slate-500">Name: </span>
                <span className="font-medium">{meta.name}</span>
              </div>
            )}
            {meta.description && (
              <div>
                <span className="text-slate-500">Description: </span>
                <span>{meta.description}</span>
              </div>
            )}
            {meta.notes && (
              <div>
                <span className="text-slate-500">Notes:</span>
                <pre className="whitespace-pre-wrap font-mono bg-slate-50 border border-slate-100 rounded p-2 mt-1">
                  {meta.notes}
                </pre>
              </div>
            )}
            {meta.columns && meta.columns.length > 0 && (
              <div>
                <div className="text-slate-500 mb-1">Columns:</div>
                <table className="text-xs border-collapse w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="border border-slate-200 px-2 py-1 text-left">
                        name
                      </th>
                      <th className="border border-slate-200 px-2 py-1 text-left">
                        role
                      </th>
                      <th className="border border-slate-200 px-2 py-1 text-left">
                        dtype
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {meta.columns.map((c, i) => (
                      <tr key={i}>
                        <td className="border border-slate-200 px-2 py-1 font-mono">
                          {String(c.name ?? "")}
                        </td>
                        <td className="border border-slate-200 px-2 py-1">
                          {String(c.role ?? "")}
                        </td>
                        <td className="border border-slate-200 px-2 py-1">
                          {String(c.dtype ?? "")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {editing && (
          <div className="space-y-3">
            <label className="block text-xs">
              <span className="text-slate-600">Name</span>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="mt-1 w-full text-sm px-2 py-1 border border-slate-200 rounded font-mono"
              />
            </label>
            <label className="block text-xs">
              <span className="text-slate-600">Description</span>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={2}
                className="mt-1 w-full text-sm px-2 py-1 border border-slate-200 rounded"
              />
            </label>
            <label className="block text-xs">
              <span className="text-slate-600">Notes</span>
              <textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                rows={4}
                className="mt-1 w-full text-sm px-2 py-1 border border-slate-200 rounded"
              />
            </label>
            <label className="block text-xs">
              <span className="text-slate-600">
                Columns (JSON array of{" "}
                <code className="font-mono">{`{name, role, dtype}`}</code>)
              </span>
              <textarea
                value={editColumnsJson}
                onChange={(e) => {
                  setEditColumnsJson(e.target.value);
                  setEditColumnsErr(null);
                }}
                rows={6}
                className="mt-1 w-full text-xs px-2 py-1 border border-slate-200 rounded font-mono"
              />
              {editColumnsErr && (
                <p className="mt-1 text-red-700">{editColumnsErr}</p>
              )}
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void saveEdit()}
                disabled={saving}
                className="text-xs px-3 py-1.5 rounded bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save sidecar"}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                disabled={saving}
                className="text-xs px-3 py-1.5 rounded border border-slate-200 hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
          {error}
        </p>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => void useForFit()}
          disabled={promoting}
          className="text-sm px-4 py-2 rounded bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {promoting ? "Loading..." : "Use for fit →"}
        </button>
      </div>
    </div>
  );
}
