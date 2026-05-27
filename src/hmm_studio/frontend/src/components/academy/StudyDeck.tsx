import { useState } from "react";
import { Flashcard } from "./Flashcard";
import type { Flashcard as FlashcardData } from "./lessonQuiz";

const navBtn =
  "px-3 py-1.5 rounded text-sm font-medium bg-slate-200 text-slate-700 hover:bg-slate-300 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed";

export function StudyDeck({ cards }: { cards: FlashcardData[] }) {
  const [i, setI] = useState(0);
  if (cards.length === 0) return null;
  return (
    <div>
      {/* key={i} remounts the card so its flip state resets when you navigate */}
      <Flashcard key={i} card={cards[i]} />
      <div className="flex items-center justify-between mt-3 text-sm">
        <button type="button" disabled={i === 0} onClick={() => setI((n) => n - 1)} className={navBtn}>
          ← Prev
        </button>
        <span className="text-slate-500">
          {i + 1} / {cards.length}
        </span>
        <button
          type="button"
          disabled={i === cards.length - 1}
          onClick={() => setI((n) => n + 1)}
          className={navBtn}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
