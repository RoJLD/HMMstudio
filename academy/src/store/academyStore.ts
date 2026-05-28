import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { CogLevel } from "../components/academy/lessonQuiz";
import type { QuizResult } from "../components/academy/scoreQuiz";

export interface StoredQuizResult {
  bestCorrect: number;
  total: number;
  byLevel: Record<CogLevel, { correct: number; total: number }>;
  missedConcepts: string[];
  at: string; // ISO date of the best attempt
}

interface AcademyState {
  completedLessons: string[];   // lesson IDs the user has marked complete
  bookmarkedLessons: string[];  // pinned for quick access
  quizResults: Record<string, StoredQuizResult>; // best quiz result per lesson id
  markCompleted: (id: string) => void;
  unmarkCompleted: (id: string) => void;
  toggleBookmark: (id: string) => void;
  recordQuizResult: (lessonId: string, result: QuizResult) => void;
  reset: () => void;
}

export const useAcademyStore = create<AcademyState>()(
  persist(
    (set) => ({
      completedLessons: [],
      bookmarkedLessons: [],
      quizResults: {},
      markCompleted: (id) =>
        set((s) => ({
          completedLessons: s.completedLessons.includes(id)
            ? s.completedLessons
            : [...s.completedLessons, id],
        })),
      unmarkCompleted: (id) =>
        set((s) => ({
          completedLessons: s.completedLessons.filter((x) => x !== id),
        })),
      toggleBookmark: (id) =>
        set((s) => ({
          bookmarkedLessons: s.bookmarkedLessons.includes(id)
            ? s.bookmarkedLessons.filter((x) => x !== id)
            : [...s.bookmarkedLessons, id],
        })),
      recordQuizResult: (lessonId, result) =>
        set((s) => {
          const prev = s.quizResults[lessonId];
          if (prev && prev.bestCorrect >= result.correct) return s; // keep the better attempt
          return {
            quizResults: {
              ...s.quizResults,
              [lessonId]: {
                bestCorrect: result.correct,
                total: result.total,
                byLevel: result.byLevel,
                missedConcepts: result.missedConcepts,
                at: new Date().toISOString(),
              },
            },
          };
        }),
      reset: () => set({ completedLessons: [], bookmarkedLessons: [], quizResults: {} }),
    }),
    {
      name: "hmm-studio-academy",
      storage: createJSONStorage(() => localStorage),
      version: 2,
      migrate: (persisted, version) => {
        // v1 had no quizResults; add it without dropping completed/bookmarks.
        const s = (persisted ?? {}) as Record<string, unknown>;
        if (version < 2 || !("quizResults" in s)) {
          return { ...s, quizResults: {} } as unknown as AcademyState;
        }
        return s as unknown as AcademyState;
      },
    },
  ),
);
