import { useCallback, useRef, useState } from "react";

interface DataDropZoneProps {
  onFile: (file: File) => void;
  uploading: boolean;
}

export function DataDropZone({ onFile, uploading }: DataDropZoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  const onChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFile(file);
      e.target.value = "";
    },
    [onFile],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={
        "border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors " +
        (dragOver
          ? "border-brand-500 bg-brand-50"
          : uploading
          ? "border-slate-300 bg-slate-50 cursor-wait"
          : "border-slate-300 hover:border-brand-500 hover:bg-slate-50")
      }
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        onChange={onChange}
        style={{ display: "none" }}
        disabled={uploading}
        data-testid="dataset-upload-input"
      />
      {uploading ? (
        <div>
          <div className="inline-block w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mb-2" />
          <p className="text-slate-600 text-sm">Uploading&hellip;</p>
        </div>
      ) : (
        <>
          <p className="text-slate-700 font-medium mb-1">
            Drop a CSV file here, or click to browse
          </p>
          <p className="text-slate-500 text-xs">Max 50 MB</p>
        </>
      )}
    </div>
  );
}
