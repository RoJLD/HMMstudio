import { LESSONS, CATEGORIES } from "../lessons";
import { LessonCard } from "../components/academy/LessonCard";
import { useAcademyStore } from "../store/academyStore";

export default function AcademyPage() {
  const completed = useAcademyStore((s) => s.completedLessons);
  const bookmarked = useAcademyStore((s) => s.bookmarkedLessons);
  const quizResults = useAcademyStore((s) => s.quizResults);

  const published = LESSONS.filter((l) => l.status === "published");
  const planned = LESSONS.filter((l) => l.status === "planned");
  const completedCount = published.filter((l) => completed.includes(l.id)).length;

  // Global step number (1..N) in category-then-order sequence, computed so it
  // stays correct as lessons are added or reordered.
  const ordered = CATEGORIES.flatMap((cat) =>
    LESSONS.filter((l) => l.category === cat.id).sort((a, b) => a.order - b.order),
  );
  const stepById = new Map(ordered.map((l, i) => [l.id, i + 1] as const));

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">Academy</h2>
      <p className="text-slate-600 mb-6">
        Interactive lessons that get you from "what's an HMM?" to "I can
        configure an NHMM with constraints." {published.length} published,{" "}
        {planned.length} planned. Progress saves locally in your browser.
      </p>

      {published.length > 0 && (
        <div className="text-sm text-slate-700 mb-4">
          Completed: <strong>{completedCount}</strong> / {published.length}{" "}
          published lesson{published.length !== 1 ? "s" : ""}
          {bookmarked.length > 0 && <> · Bookmarked: {bookmarked.length}</>}
        </div>
      )}

      {CATEGORIES.map((cat) => {
        const lessons = LESSONS.filter((l) => l.category === cat.id).sort(
          (a, b) => a.order - b.order,
        );
        if (lessons.length === 0) return null;
        return (
          <section key={cat.id} className="mb-8">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
              {cat.title}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {lessons.map((lesson) => (
                <LessonCard
                  key={lesson.id}
                  lesson={lesson}
                  step={stepById.get(lesson.id)}
                  completed={completed.includes(lesson.id)}
                  bookmarked={bookmarked.includes(lesson.id)}
                  quizScore={
                    quizResults[lesson.id]
                      ? {
                          bestCorrect: quizResults[lesson.id].bestCorrect,
                          total: quizResults[lesson.id].total,
                        }
                      : undefined
                  }
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
