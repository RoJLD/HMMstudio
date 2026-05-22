import type { MouseEventHandler } from "react";

interface ExportButtonProps {
  onClick: MouseEventHandler<HTMLButtonElement>;
  label?: string;
}

export function ExportButton({ onClick, label = "Download SVG" }: ExportButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-xs text-slate-500 hover:text-brand-700 underline px-2 py-1"
      title="Download as SVG (open in browser or Inkscape for PNG)"
    >
      ↓ {label}
    </button>
  );
}
