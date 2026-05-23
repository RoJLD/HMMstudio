import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { uploadDataset, type WarehouseList } from "../api/client";
import { useDatasetStore } from "../store/datasetStore";
import { DataDropZone } from "../components/data/DataDropZone";
import { DatasetPreviewCard } from "../components/data/DatasetPreviewCard";
import { DatasetHistoryList } from "../components/data/DatasetHistoryList";
import { AnnotationsPanel } from "../components/data/AnnotationsPanel";
import { WarehouseSidebar } from "../components/data/WarehouseSidebar";
import { WarehousePreviewPanel } from "../components/data/WarehousePreviewPanel";

export default function DataPage() {
  const current = useDatasetStore((s) => s.current);
  const setCurrent = useDatasetStore((s) => s.setCurrent);
  const addToHistory = useDatasetStore((s) => s.addToHistory);
  const history = useDatasetStore((s) => s.history);

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedWarehouseRelPath, setSelectedWarehouseRelPath] = useState<
    string | null
  >(null);
  const [warehouseList, setWarehouseList] = useState<WarehouseList | null>(
    null,
  );
  const [hintDismissed, setHintDismissed] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setUploading(true);
      try {
        const preview = await uploadDataset(file);
        setCurrent(preview);
        addToHistory(preview);
        // Clear warehouse selection so the local upload visibly takes over.
        setSelectedWarehouseRelPath(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "upload failed");
      } finally {
        setUploading(false);
      }
    },
    [setCurrent, addToHistory],
  );

  const handleWarehouseSelect = useCallback(
    (relPath: string) => {
      setSelectedWarehouseRelPath(relPath);
      // Hide the local-upload preview while the warehouse panel is showing,
      // so the user has one source of truth on screen.
      setCurrent(null);
    },
    [setCurrent],
  );

  const warehouseConfigured =
    warehouseList !== null && warehouseList.warehouse_path !== "";
  const showSidebar = warehouseConfigured;

  // The local-upload section: keep DRY across single- and two-column layouts.
  const localFlow = (
    <>
      <DataDropZone onFile={handleFile} uploading={uploading} />

      {error && (
        <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      {selectedWarehouseRelPath ? (
        <div className="mt-6">
          <WarehousePreviewPanel relPath={selectedWarehouseRelPath} />
        </div>
      ) : (
        <>
          {current && (
            <div className="mt-6">
              <DatasetPreviewCard preview={current} />
            </div>
          )}

          {current && (
            <div className="mt-6">
              <AnnotationsPanel datasetId={current.id} />
            </div>
          )}
        </>
      )}

      {history.length > 1 && (
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-slate-500 uppercase mb-2">
            Recent uploads
          </h3>
          <DatasetHistoryList history={history} onSelect={setCurrent} />
        </div>
      )}
    </>
  );

  return (
    <div className={showSidebar ? "max-w-7xl" : "max-w-5xl"}>
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">Data</h2>
      <p className="text-slate-600 mb-6">
        Upload a CSV. For Gaussian / GMM / Poisson emissions, columns are
        the observation features. For Multinomial emissions, the CSV must
        have a single integer column with values in <code>[0, n_symbols)</code>.
      </p>

      {/* Hint banner when warehouse is not configured */}
      {warehouseList && !warehouseConfigured && !hintDismissed && (
        <div className="mb-4 flex items-start justify-between gap-3 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded px-3 py-2">
          <span>
            <span className="font-mono text-slate-500 mr-1">[?]</span>
            No warehouse configured.{" "}
            <Link
              to="/settings"
              className="text-brand-700 underline hover:text-brand-800"
            >
              Open settings
            </Link>{" "}
            to set one and enable directory-based dataset browsing. (The{" "}
            <code className="font-mono bg-white px-1 rounded">
              HMM_STUDIO_WAREHOUSE_PATH
            </code>{" "}
            environment variable still works as the initial default.)
          </span>
          <button
            type="button"
            onClick={() => setHintDismissed(true)}
            className="shrink-0 text-slate-500 hover:text-slate-700"
            aria-label="dismiss hint"
          >
            ×
          </button>
        </div>
      )}

      {showSidebar ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <WarehouseSidebar
              onListLoaded={setWarehouseList}
              selectedRelPath={selectedWarehouseRelPath}
              onSelect={handleWarehouseSelect}
            />
          </div>
          <div className="lg:col-span-2">{localFlow}</div>
        </div>
      ) : (
        <>
          {/* Mount the sidebar invisibly so we can detect whether a warehouse
              is configured without forcing the user to see an empty panel. */}
          {!warehouseList && (
            <div className="hidden">
              <WarehouseSidebar
                onListLoaded={setWarehouseList}
                selectedRelPath={null}
                onSelect={() => undefined}
              />
            </div>
          )}
          {localFlow}
        </>
      )}
    </div>
  );
}
