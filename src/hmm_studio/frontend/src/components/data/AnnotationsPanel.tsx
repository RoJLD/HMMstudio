import { useCallback, useEffect, useRef, useState } from "react";
import {
  listAnnotations,
  uploadAnnotations,
  deleteAnnotation,
  type AnnotationOut,
} from "../../api/client";

interface AnnotationsPanelProps {
  datasetId: string;
}

export function AnnotationsPanel({ datasetId }: AnnotationsPanelProps) {
  const [annotations, setAnnotations] = useState<AnnotationOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await listAnnotations(datasetId);
      setAnnotations(r.annotations);
    } catch (e) {
      setError(e instanceof Error ? e.message : "load failed");
    }
  }, [datasetId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleFile = async (file: File) => {
    setError(null);
    setUploading(true);
    try {
      const r = await uploadAnnotations(datasetId, file);
      setAnnotations(r.annotations);
    } catch (e) {
      setError(e instanceof Error ? e.message : "upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAnnotation(datasetId, id);
      setAnnotations((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "delete failed");
    }
  };

  return (
    <div className="border border-slate-200 rounded-md bg-white p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="font-semibold text-slate-900">Annotations</h3>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-40"
        >
          {uploading ? "Uploading…" : "↑ Upload CSV"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
            e.target.value = "";
          }}
        />
      </div>
      <p className="text-xs text-slate-500 mb-3">
        CSV columns: <code>t,label[,color]</code>. Re-uploading replaces all
        annotations for this dataset.
      </p>

      {error && (
        <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1 mb-3">
          {error}
        </p>
      )}

      {annotations.length === 0 ? (
        <p className="text-xs text-slate-500">No annotations yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100 text-sm">
          {annotations.map((a) => (
            <li
              key={a.id}
              className="py-1.5 flex items-center gap-2"
            >
              <span
                className="inline-block w-3 h-3 rounded-sm"
                style={{ background: a.color || "#94a3b8" }}
              />
              <span className="font-mono text-xs text-slate-500 w-12 text-right">
                {a.t}
              </span>
              <span className="flex-1 text-slate-800 truncate">{a.label}</span>
              <button
                type="button"
                onClick={() => handleDelete(a.id)}
                className="text-xs text-red-600 hover:text-red-800"
                title="Delete"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
