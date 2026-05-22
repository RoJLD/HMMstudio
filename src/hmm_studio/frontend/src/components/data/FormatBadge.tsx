interface Props {
  format: string;
}

// Distinct tailwind palette per format. Kept inline (not a Record map) so
// tailwind's JIT picks up every class via static analysis.
function classesFor(format: string): string {
  switch (format.toLowerCase()) {
    case "csv":
      return "bg-green-100 text-green-800 border border-green-200";
    case "parquet":
      return "bg-purple-100 text-purple-800 border border-purple-200";
    case "json":
    case "jsonl":
      return "bg-amber-100 text-amber-800 border border-amber-200";
    case "xlsx":
    case "xls":
      return "bg-emerald-100 text-emerald-800 border border-emerald-200";
    case "feather":
      return "bg-sky-100 text-sky-800 border border-sky-200";
    case "tsv":
      return "bg-slate-100 text-slate-800 border border-slate-200";
    default:
      return "bg-slate-100 text-slate-700 border border-slate-200";
  }
}

export function FormatBadge({ format }: Props) {
  return (
    <span
      className={`px-1.5 py-0.5 text-xs font-mono rounded uppercase ${classesFor(format)}`}
    >
      {format}
    </span>
  );
}
