import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { EditorCanvas } from "../components/topology/EditorCanvas";
import { Toolbar } from "../components/topology/Toolbar";
import { SidePanel } from "../components/topology/SidePanel";
import { useTopologyStore } from "../store/topologyStore";
import { topologyToYAML, yamlToTopology } from "../lib/yaml";
import { useDebouncedValidation } from "../hooks/useDebouncedValidation";
import { buildShareUrl, clearTopologyParam, readSharedTopology } from "../lib/share";

export default function TopologyPage() {
  const validation = useDebouncedValidation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  // On mount: hydrate topology from ?topology= URL param if present
  useEffect(() => {
    const shared = readSharedTopology();
    if (shared) {
      useTopologyStore.getState().loadTopology(shared);
      clearTopologyParam();
      setShareStatus("Loaded topology from shared URL");
      setTimeout(() => setShareStatus(null), 3000);
    }
  }, []);

  async function handleShare() {
    const state = useTopologyStore.getState();
    if (state.states.length === 0) {
      setShareStatus("Empty topology — nothing to share");
      setTimeout(() => setShareStatus(null), 3000);
      return;
    }
    const url = buildShareUrl(state);
    try {
      await navigator.clipboard.writeText(url);
      setShareStatus("Link copied to clipboard");
    } catch {
      setShareStatus("Copy failed — URL: " + url);
    }
    setTimeout(() => setShareStatus(null), 4000);
  }

  function handleExport() {
    const state = useTopologyStore.getState();
    const yamlText = topologyToYAML(state);
    const blob = new Blob([yamlText], { type: "application/x-yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.name || "topology"}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImportClick() {
    fileInputRef.current?.click();
  }

  function handleImportFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = String(reader.result);
        const partial = yamlToTopology(text);
        useTopologyStore.getState().loadTopology(partial);
      } catch (e) {
        // eslint-disable-next-line no-alert
        alert(`Failed to import YAML: ${e instanceof Error ? e.message : "?"}`);
      }
    };
    reader.readAsText(file);
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] -mx-8 -my-8">
      <div className="flex-1 flex flex-col p-4 min-w-0">
        <div className="mb-2">
          <Link
            to="/topology/new"
            className="inline-block px-3 py-1.5 rounded text-sm font-medium bg-brand-600 text-white hover:bg-brand-700"
          >
            ✨ New guided model
          </Link>
        </div>
        <Toolbar
          onValidate={() => {
            // Validation is debounced and runs automatically on every change.
            // This button is a no-op trigger; useful as a "refresh" affordance.
          }}
          onExport={handleExport}
          onImport={handleImportClick}
          onShare={handleShare}
        />
        {shareStatus && (
          <p className="mb-2 text-xs text-brand-700 bg-brand-50 border border-brand-200 rounded px-2 py-1">
            {shareStatus}
          </p>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".yaml,.yml"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleImportFile(f);
            e.target.value = "";
          }}
        />
        <EditorCanvas />
      </div>
      <SidePanel
        validationError={validation.error}
        validationSummary={validation.summary}
      />
    </div>
  );
}
