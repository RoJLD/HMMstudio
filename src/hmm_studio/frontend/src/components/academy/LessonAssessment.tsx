import { useState } from "react";
import { getLessonQuiz } from "./lessonQuiz";
import { StudyDeck } from "./StudyDeck";
import { QuizRunner } from "./QuizRunner";

function tabCls(active: boolean): string {
  return (
    "px-3 py-1.5 rounded text-sm font-medium " +
    (active ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200")
  );
}

/** End-of-lesson "Check your understanding": a flashcard deck + a graded quiz.
 *  Renders nothing if the lesson has no quiz content. */
export function LessonAssessment({ lessonId }: { lessonId: string }) {
  const quiz = getLessonQuiz(lessonId);
  const [tab, setTab] = useState<"deck" | "quiz">("deck");
  if (!quiz) return null;

  return (
    <div className="mt-10 pt-6 border-t border-slate-200">
      <h2 className="text-xl font-semibold text-slate-900 mb-1">Check your understanding</h2>
      <p className="text-sm text-slate-500 mb-4">
        Revise with the flashcards, then take the graded quiz for a score and a gap report.
      </p>
      <div className="flex gap-2 mb-4">
        <button type="button" onClick={() => setTab("deck")} className={tabCls(tab === "deck")}>
          Study deck ({quiz.flashcards.length})
        </button>
        <button type="button" onClick={() => setTab("quiz")} className={tabCls(tab === "quiz")}>
          Take quiz ({quiz.questions.length})
        </button>
      </div>
      {tab === "deck" ? (
        <StudyDeck cards={quiz.flashcards} />
      ) : (
        <QuizRunner lessonId={lessonId} questions={quiz.questions} />
      )}
    </div>
  );
}
