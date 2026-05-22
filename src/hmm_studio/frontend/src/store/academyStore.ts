import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface AcademyState {
  completedLessons: string[];   // lesson IDs the user has marked complete
  bookmarkedLessons: string[];  // pinned for quick access
  markCompleted: (id: string) => void;
  unmarkCompleted: (id: string) => void;
  toggleBookmark: (id: string) => void;
  reset: () => void;
}

export const useAcademyStore = create<AcademyState>()(
  persist(
    (set) => ({
      completedLessons: [],
      bookmarkedLessons: [],
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
      reset: () => set({ completedLessons: [], bookmarkedLessons: [] }),
    }),
    {
      name: "hmm-studio-academy",
      storage: createJSONStorage(() => localStorage),
      version: 1,
    },
  ),
);
