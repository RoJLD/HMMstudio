import { LESSONS } from "../lessons";
import { LessonCard } from "../components/academy/LessonCard";
import { useAcademyStore } from "../store/academyStore";

export default function AcademyPage() {
  const completed = useAcademyStore((s) => s.completedLessons);
  const bookmarked = useAcademyStore((s) => s.bookmarkedLessons);

  const published = LESSONS.filter((l) => l.status === "published");
  const planned = LESSONS.filter((l) => l.status === "planned");
  const completedCount = published.filter((l) => completed.includes(l.id)).length;

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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {LESSONS.map((lesson) => (
          <LessonCard
            key={lesson.id}
            lesson={lesson}
            completed={completed.includes(lesson.id)}
            bookmarked={bookmarked.includes(lesson.id)}
          />
        ))}
      </div>
    </div>
  );
}
