import type { CogLevel, QuizQuestion } from "./lessonQuiz";

export const COG_LEVELS: CogLevel[] = ["Recall", "Apply", "Analyze"];

export interface QuizResult {
  total: number;
  correct: number;
  byLevel: Record<CogLevel, { correct: number; total: number }>;
  missedConcepts: string[];
}

/** Grade answers against the questions. Pure — easy to unit-test.
 *  `answers[i]` is the chosen option index for question i, or null if skipped. */
export function scoreQuiz(questions: QuizQuestion[], answers: (number | null)[]): QuizResult {
  const byLevel: Record<CogLevel, { correct: number; total: number }> = {
    Recall: { correct: 0, total: 0 },
    Apply: { correct: 0, total: 0 },
    Analyze: { correct: 0, total: 0 },
  };
  const missedConcepts: string[] = [];
  let correct = 0;

  questions.forEach((q, i) => {
    byLevel[q.level].total += 1;
    if (answers[i] === q.correct) {
      correct += 1;
      byLevel[q.level].correct += 1;
    } else if (!missedConcepts.includes(q.concept)) {
      missedConcepts.push(q.concept);
    }
  });

  return { total: questions.length, correct, byLevel, missedConcepts };
}
