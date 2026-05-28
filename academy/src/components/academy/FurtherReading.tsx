/**
 * Reusable "Further reading" component for Academy lessons.
 *
 * Renders a list of external sourced references (PDFs, lecture notes,
 * canonical papers) at the bottom of a lesson, with a uniform style.
 *
 * The central bibliography lives in docs/sources/academy-references.md
 * (committed alongside the repo). Each lesson cites a small subset that
 * matches its scope.
 */

export interface Reference {
  /** Short, citable label, e.g. "Rabiner 1989 §III.A". */
  label: string;
  /** Full title or descriptive context (one sentence max). */
  title: string;
  /** Direct URL (PDF or article page). */
  url: string;
  /** Optional one-liner explaining why this ref is worth reading here. */
  note?: string;
}

interface FurtherReadingProps {
  references: Reference[];
}

export function FurtherReading({ references }: FurtherReadingProps) {
  if (references.length === 0) return null;
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-10">
        Further reading
      </h2>
      <p className="text-slate-600 text-sm mb-3">
        Sourced PDFs and canonical papers that deepen the topics covered
        above. See{" "}
        <a
          href="https://github.com/RoJLD/HMMstudio/blob/main/docs/sources/academy-references.md"
          target="_blank"
          rel="noreferrer"
          className="text-indigo-600 hover:underline"
        >
          docs/sources/academy-references.md
        </a>{" "}
        for the full bibliography.
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        {references.map((ref) => (
          <li key={ref.url}>
            <a
              href={ref.url}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-600 hover:underline font-medium"
            >
              {ref.label}
            </a>{" "}
            — {ref.title}
            {ref.note && (
              <span className="text-slate-500 text-sm"> ({ref.note})</span>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
