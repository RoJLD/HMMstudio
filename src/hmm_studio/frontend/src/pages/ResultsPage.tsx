import { useParams } from "react-router-dom";

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-2">Results</h2>
      <p className="text-slate-600">
        Heatmap + Viterbi for job <code>{jobId}</code> — planned for B.6.
      </p>
    </div>
  );
}
