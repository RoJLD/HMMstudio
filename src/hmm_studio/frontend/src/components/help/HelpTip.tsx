import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PARAM_HELP } from "./paramHelp";

interface HelpTipProps {
  paramKey: string;
  // Which edge the popover aligns to. "left" (default) extends to the right;
  // "right" extends to the left (use near a right-hand panel edge).
  align?: "left" | "right";
}

export function HelpTip({ paramKey, align = "left" }: HelpTipProps) {
  const entry = PARAM_HELP[paramKey];
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Unknown key → render nothing (no orphan "?").
  if (!entry) return null;

  return (
    <span ref={wrapRef} className="relative inline-flex items-center">
      <button
        type="button"
        aria-label={`Help: ${entry.title}`}
        aria-expanded={open}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="ml-1 w-4 h-4 inline-flex items-center justify-center rounded-full border border-slate-300 text-[10px] leading-none text-slate-500 hover:bg-brand-600 hover:text-white hover:border-brand-600"
      >
        ?
      </button>
      {open && (
        <div
          role="dialog"
          onClick={(e) => e.stopPropagation()}
          className={
            "absolute top-full mt-1 z-50 w-64 rounded-md border border-slate-200 bg-white p-3 shadow-lg text-left font-normal normal-case " +
            (align === "right" ? "right-0" : "left-0")
          }
        >
          <div className="text-xs font-semibold text-slate-800 mb-1">{entry.title}</div>
          <div className="text-xs text-slate-600 leading-snug">{entry.body}</div>
          {entry.lesson && (
            <Link
              to={`/academy/${entry.lesson.id}`}
              onClick={() => setOpen(false)}
              className="mt-2 inline-block text-xs text-indigo-600 hover:underline"
            >
              Learn more → {entry.lesson.label}
            </Link>
          )}
        </div>
      )}
    </span>
  );
}
