import { Link, useParams } from "react-router-dom";
import { NotebookLink } from "../components/academy/NotebookLink";
import { LessonAssessment } from "../components/academy/LessonAssessment";
import { TryInStudioLink } from "../components/TryInStudioLink";
import { getLessonById, LESSONS } from "../lessons";
import { useAcademyStore } from "../store/academyStore";

export default function LessonPage() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const lesson = lessonId ? getLessonById(lessonId) : undefined;
  const completed = useAcademyStore((s) => s.completedLessons);
  const markCompleted = useAcademyStore((s) => s.markCompleted);
  const unmarkCompleted = useAcademyStore((s) => s.unmarkCompleted);

  if (!lesson) {
    return (
      <div className="max-w-2xl">
        <h2 className="text-2xl font-semibold text-slate-900 mb-2">
          Lesson not found
        </h2>
        <Link to="/academy" className="text-brand-700 hover:underline">
          ← Back to Academy
        </Link>
      </div>
    );
  }

  if (lesson.status === "planned") {
    return (
      <div className="max-w-2xl">
        <Link to="/academy" className="text-brand-700 hover:underline text-sm">
          ← Back to Academy
        </Link>
        <h2 className="text-2xl font-semibold text-slate-900 mb-2 mt-2">
          {lesson.title}
        </h2>
        <p className="text-slate-600">
          This lesson is planned but not yet published.{" "}
          {lesson.description}
        </p>
      </div>
    );
  }

  const isDone = completed.includes(lesson.id);

  // Prev / Next navigation
  const publishedSequence = LESSONS.filter((l) => l.status === "published");
  const idx = publishedSequence.findIndex((l) => l.id === lesson.id);
  const prev = idx > 0 ? publishedSequence[idx - 1] : null;
  const next = idx < publishedSequence.length - 1 ? publishedSequence[idx + 1] : null;

  return (
    <div className="max-w-3xl">
      <Link to="/academy" className="text-brand-700 hover:underline text-sm">
        ← Back to Academy
      </Link>

      <div className="mt-2 mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          {lesson.title}
        </h1>
        <p className="text-slate-500 text-sm">
          Estimated time: {lesson.estimatedMinutes} min · Difficulty:{" "}
          {lesson.difficulty}
        </p>
      </div>

      <TryInStudioLink yaml={lesson.presetTopologyYaml} />

      <div className="text-slate-800 leading-relaxed">
        {lesson.content?.()}
      </div>

      {lesson.notebookLink && <NotebookLink notebook={lesson.notebookLink} />}

      <LessonAssessment lessonId={lesson.id} />

      <div className="mt-8 pt-6 border-t border-slate-200 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => (isDone ? unmarkCompleted(lesson.id) : markCompleted(lesson.id))}
          className={
            "px-4 py-2 rounded text-sm font-medium " +
            (isDone
              ? "bg-green-100 text-green-800 hover:bg-green-200"
              : "bg-brand-600 text-white hover:bg-brand-700")
          }
        >
          {isDone ? "✓ Marked complete" : "Mark as complete"}
        </button>

        <div className="flex items-center gap-3 text-sm">
          {prev && (
            <Link to={`/academy/${prev.id}`} className="text-brand-700 hover:underline">
              ← {prev.title}
            </Link>
          )}
          {next && (
            <Link to={`/academy/${next.id}`} className="text-brand-700 hover:underline">
              {next.title} →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
