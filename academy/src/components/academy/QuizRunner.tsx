import { useState } from "react";
import type { QuizQuestion } from "./lessonQuiz";
import { scoreQuiz, COG_LEVELS, type QuizResult } from "./scoreQuiz";
import { useAcademyStore } from "../../store/academyStore";

const LEVEL_COLORS: Record<string, string> = {
  Recall: "bg-green-100 text-green-800",
  Apply: "bg-yellow-100 text-yellow-800",
  Analyze: "bg-orange-100 text-orange-800",
};

export function QuizRunner({
  lessonId,
  questions,
}: {
  lessonId: string;
  questions: QuizQuestion[];
}) {
  const [answers, setAnswers] = useState<(number | null)[]>(() => questions.map(() => null));
  const [result, setResult] = useState<QuizResult | null>(null);
  const recordQuizResult = useAcademyStore((s) => s.recordQuizResult);

  const allAnswered = answers.every((a) => a !== null);

  function choose(qi: number, oi: number) {
    if (result) return;
    setAnswers((prev) => {
      const next = [...prev];
      next[qi] = oi;
      return next;
    });
  }

  function submit() {
    const r = scoreQuiz(questions, answers);
    setResult(r);
    recordQuizResult(lessonId, r);
  }

  function retry() {
    setAnswers(questions.map(() => null));
    setResult(null);
  }

  return (
    <div className="space-y-4">
      {result && (
        <div className="border border-slate-200 rounded-md p-4 bg-slate-50">
          <p className="text-lg font-semibold text-slate-800">
            Score: {result.correct} / {result.total}
          </p>
          <div className="mt-2 space-y-1">
            {COG_LEVELS.map((lv) => {
              const b = result.byLevel[lv];
              if (b.total === 0) return null;
              const ok = b.correct === b.total;
              return (
                <div key={lv} className="flex items-center gap-2 text-sm">
                  <span
                    className={
                      "text-xs px-2 py-0.5 rounded font-medium w-20 text-center " +
                      (LEVEL_COLORS[lv] ?? "")
                    }
                  >
                    {lv}
                  </span>
                  <span
                    className={
                      ok ? "text-green-700" : b.correct === 0 ? "text-red-700" : "text-slate-600"
                    }
                  >
                    {b.correct}/{b.total}
                  </span>
                </div>
              );
            })}
          </div>
          {result.missedConcepts.length > 0 ? (
            <p className="mt-3 text-sm text-slate-700">
              Gaps to revisit: <span className="font-medium">{result.missedConcepts.join(", ")}</span>.
            </p>
          ) : (
            <p className="mt-3 text-sm text-green-700">Perfect — no gaps. 🎉</p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={retry}
              className="px-3 py-1.5 rounded text-sm font-medium bg-brand-600 text-white hover:bg-brand-700"
            >
              Retry
            </button>
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="px-3 py-1.5 rounded text-sm font-medium bg-slate-200 text-slate-700 hover:bg-slate-300"
            >
              Review lesson ↑
            </button>
          </div>
        </div>
      )}

      {questions.map((q, qi) => {
        const chosen = answers[qi];
        return (
          <div key={qi} className="border border-slate-200 rounded-md p-3 bg-white">
            <p className="text-sm font-medium text-slate-800 mb-2">
              {qi + 1}. {q.prompt}
            </p>
            <div className="space-y-1">
              {q.options.map((opt, oi) => {
                const isChosen = chosen === oi;
                const isCorrect = oi === q.correct;
                let cls = "border-slate-200";
                if (result) {
                  if (isCorrect) cls = "border-green-400 bg-green-50";
                  else if (isChosen) cls = "border-red-400 bg-red-50";
                } else if (isChosen) {
                  cls = "border-brand-400 bg-brand-50";
                }
                return (
                  <button
                    key={oi}
                    type="button"
                    disabled={!!result}
                    onClick={() => choose(qi, oi)}
                    className={
                      "w-full text-left text-sm px-2 py-1.5 rounded border " +
                      cls +
                      (result ? " cursor-default" : " hover:border-brand-300")
                    }
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
            {result && <p className="mt-2 text-xs text-slate-500">{q.explanation}</p>}
          </div>
        );
      })}

      {!result && (
        <button
          type="button"
          disabled={!allAnswered}
          onClick={submit}
          className={
            "px-4 py-2 rounded text-sm font-medium " +
            (allAnswered
              ? "bg-brand-600 text-white hover:bg-brand-700"
              : "bg-slate-200 text-slate-500 cursor-not-allowed")
          }
        >
          Submit quiz
        </button>
      )}
    </div>
  );
}
