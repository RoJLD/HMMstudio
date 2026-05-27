import { Link } from "react-router-dom";
import type { LessonMeta } from "../../lessons";

interface LessonCardProps {
  lesson: LessonMeta;
  completed: boolean;
  bookmarked: boolean;
  // Global step number (1..N) across the ordered curriculum, shown before the title.
  step?: number;
  // Best quiz result so far (if the user has taken this lesson's quiz).
  quizScore?: { bestCorrect: number; total: number };
}

const DIFF_COLORS: Record<LessonMeta["difficulty"], string> = {
  Beginner: "bg-green-100 text-green-800",
  Intermediate: "bg-yellow-100 text-yellow-800",
  Advanced: "bg-orange-100 text-orange-800",
};

export function LessonCard({ lesson, completed, bookmarked, step, quizScore }: LessonCardProps) {
  const planned = lesson.status === "planned";
  const className =
    "block p-4 border rounded-md transition-colors " +
    (planned
      ? "border-slate-200 bg-slate-50 text-slate-500 cursor-not-allowed"
      : "border-slate-200 bg-white hover:border-brand-400 hover:shadow-sm cursor-pointer");

  const inner = (
    <>
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <h3 className="font-semibold text-base">
          {step != null && (
            <span className="text-slate-400 font-mono mr-1.5">{step}.</span>
          )}
          {lesson.title}
        </h3>
        {completed && !planned && (
          <span className="text-green-700 text-sm">✓</span>
        )}
        {bookmarked && !planned && (
          <span className="text-amber-500 text-sm">★</span>
        )}
      </div>
      <p className="text-sm leading-relaxed mb-3">{lesson.description}</p>
      <div className="flex items-center gap-2 text-xs">
        <span
          className={
            "px-2 py-0.5 rounded font-medium " + DIFF_COLORS[lesson.difficulty]
          }
        >
          {lesson.difficulty}
        </span>
        <span className="text-slate-500">{lesson.estimatedMinutes} min</span>
        {quizScore && !planned && (
          <span className="px-2 py-0.5 rounded font-medium bg-indigo-100 text-indigo-800">
            Quiz {quizScore.bestCorrect}/{quizScore.total}
          </span>
        )}
        {planned && (
          <span className="text-slate-500 italic ml-auto">Planned</span>
        )}
      </div>
    </>
  );

  if (planned) {
    return <div className={className}>{inner}</div>;
  }
  return (
    <Link to={`/academy/${lesson.id}`} className={className}>
      {inner}
    </Link>
  );
}
