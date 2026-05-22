import type { DatasetPreview } from "../../api/client";

interface DatasetHistoryListProps {
  history: DatasetPreview[];
  onSelect: (ds: DatasetPreview) => void;
}

export function DatasetHistoryList({ history, onSelect }: DatasetHistoryListProps) {
  return (
    <ul className="border border-slate-200 rounded divide-y divide-slate-100 bg-white">
      {history.map((ds) => (
        <li key={ds.id}>
          <button
            type="button"
            onClick={() => onSelect(ds)}
            className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center justify-between gap-3 text-sm"
          >
            <span className="font-medium text-slate-800 truncate">
              {ds.filename}
            </span>
            <span className="text-xs text-slate-500 shrink-0">
              {ds.n_rows} &times; {ds.n_cols}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
