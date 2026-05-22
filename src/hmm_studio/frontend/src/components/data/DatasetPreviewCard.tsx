import type { DatasetPreview } from "../../api/client";

interface DatasetPreviewCardProps {
  preview: DatasetPreview;
}

export function DatasetPreviewCard({ preview }: DatasetPreviewCardProps) {
  const cols = preview.columns;

  return (
    <div className="border border-slate-200 rounded-md bg-white p-4">
      <div className="flex items-baseline justify-between mb-3 gap-4 flex-wrap">
        <div>
          <h3 className="font-semibold text-slate-900">{preview.filename}</h3>
          <p className="text-xs text-slate-500 break-all">id: {preview.id}</p>
        </div>
        <div className="text-sm text-slate-600">
          {preview.n_rows} rows &times; {preview.n_cols} cols
        </div>
      </div>

      <div className="text-xs text-slate-500 mb-3">
        dtypes:{" "}
        {cols
          .map((c) => `${c} (${preview.dtypes[c] ?? "?"})`)
          .join(", ")}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-xs border-collapse">
          <thead className="bg-slate-50">
            <tr>
              {cols.map((c) => (
                <th
                  key={c}
                  className="border border-slate-200 px-2 py-1 text-left font-medium text-slate-700"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.head.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                {cols.map((c) => (
                  <td
                    key={c}
                    className="border border-slate-200 px-2 py-1 font-mono text-slate-800"
                  >
                    {formatCell(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500 mt-2">
        Preview shows first {preview.head.length} rows of {preview.n_rows}.
      </p>
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toString() : value.toFixed(4);
  }
  return String(value);
}
