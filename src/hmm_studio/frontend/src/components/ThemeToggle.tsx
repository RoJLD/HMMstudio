import { useTheme, type Theme } from "../hooks/useTheme";

const OPTIONS: { value: Theme; label: string; icon: string }[] = [
  { value: "light", label: "Light", icon: "☀" },
  { value: "dark", label: "Dark", icon: "☾" },
  { value: "system", label: "System", icon: "⌘" },
];

export function ThemeToggle() {
  const [theme, setTheme] = useTheme();

  return (
    <div className="flex gap-0.5 bg-slate-800/40 dark:bg-slate-700/40 rounded p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          title={opt.label}
          className={
            "px-2 py-1 text-xs rounded transition-colors " +
            (theme === opt.value
              ? "bg-brand-600 text-white"
              : "text-slate-400 hover:text-slate-200")
          }
        >
          {opt.icon}
        </button>
      ))}
    </div>
  );
}
