import { useRef } from "react";
import { EditorCanvas } from "../components/topology/EditorCanvas";
import { Toolbar } from "../components/topology/Toolbar";
import { SidePanel } from "../components/topology/SidePanel";
import { useTopologyStore } from "../store/topologyStore";
import { topologyToYAML, yamlToTopology } from "../lib/yaml";
import { useDebouncedValidation } from "../hooks/useDebouncedValidation";

export default function TopologyPage() {
  const validation = useDebouncedValidation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
        <Toolbar
          onValidate={() => {
            // Validation is debounced and runs automatically on every change.
            // This button is a no-op trigger; useful as a "refresh" affordance.
          }}
          onExport={handleExport}
          onImport={handleImportClick}
        />
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
