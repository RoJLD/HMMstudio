import { useCallback, useState } from "react";
import { uploadDataset } from "../api/client";
import { useDatasetStore } from "../store/datasetStore";
import { DataDropZone } from "../components/data/DataDropZone";
import { DatasetPreviewCard } from "../components/data/DatasetPreviewCard";
import { DatasetHistoryList } from "../components/data/DatasetHistoryList";

export default function DataPage() {
  const current = useDatasetStore((s) => s.current);
  const setCurrent = useDatasetStore((s) => s.setCurrent);
  const addToHistory = useDatasetStore((s) => s.addToHistory);
  const history = useDatasetStore((s) => s.history);

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setUploading(true);
      try {
        const preview = await uploadDataset(file);
        setCurrent(preview);
        addToHistory(preview);
      } catch (e) {
        setError(e instanceof Error ? e.message : "upload failed");
      } finally {
        setUploading(false);
      }
    },
    [setCurrent, addToHistory],
  );

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">Data</h2>
      <p className="text-slate-600 mb-6">
        Upload a CSV. For Gaussian / GMM / Poisson emissions, columns are
        the observation features. For Multinomial emissions, the CSV must
        have a single integer column with values in <code>[0, n_symbols)</code>.
      </p>

      <DataDropZone onFile={handleFile} uploading={uploading} />

      {error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      {current && (
        <div className="mt-6">
          <DatasetPreviewCard preview={current} />
        </div>
      )}

      {history.length > 1 && (
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-slate-500 uppercase mb-2">
            Recent uploads
          </h3>
          <DatasetHistoryList history={history} onSelect={setCurrent} />
        </div>
      )}
    </div>
  );
}
