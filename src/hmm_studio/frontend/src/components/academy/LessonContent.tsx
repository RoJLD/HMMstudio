import type { ReactNode } from "react";

interface LessonContentProps {
  children: ReactNode;
}

/**
 * Wraps lesson body content. Currently a thin styling wrapper; when MDX is
 * adopted this component will handle the MDX provider context.
 */
export function LessonContent({ children }: LessonContentProps) {
  return (
    <div className="lesson-content text-slate-800 leading-relaxed">
      {children}
    </div>
  );
}
