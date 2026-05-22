import { EditorCanvas } from "../components/topology/EditorCanvas";
import { Toolbar } from "../components/topology/Toolbar";
import { SidePanel } from "../components/topology/SidePanel";

export default function TopologyPage() {
  return (
    <div className="flex h-[calc(100vh-4rem)] -mx-8 -my-8">
      <div className="flex-1 flex flex-col p-4 min-w-0">
        <Toolbar
          onValidate={() => {
            // wired in B.4.1.4
          }}
          onExport={() => {
            // wired in B.4.1.4
          }}
          onImport={() => {
            // wired in B.4.1.4
          }}
        />
        <EditorCanvas />
      </div>
      <SidePanel validationError={null} validationSummary={null} />
    </div>
  );
}
