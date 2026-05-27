import { useState } from "react";
import type { Flashcard as FlashcardData } from "./lessonQuiz";

const LEVEL_COLORS: Record<string, string> = {
  Recall: "bg-green-100 text-green-800",
  Apply: "bg-yellow-100 text-yellow-800",
  Analyze: "bg-orange-100 text-orange-800",
};

export function Flashcard({ card }: { card: FlashcardData }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setFlipped((f) => !f)}
      className="w-full text-left border border-slate-200 rounded-md p-5 bg-white hover:border-brand-400 min-h-[140px] flex flex-col"
    >
      <span
        className={
          "self-start text-xs px-2 py-0.5 rounded font-medium mb-3 " +
          (LEVEL_COLORS[card.level] ?? "bg-slate-100 text-slate-700")
        }
      >
        {card.level}
      </span>
      <span className="text-slate-800">{flipped ? card.back : card.front}</span>
      <span className="mt-auto pt-3 text-xs text-slate-400">
        {flipped ? "Answer · click to flip back" : "Click to reveal the answer"}
      </span>
    </button>
  );
}
