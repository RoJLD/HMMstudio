import { useCallback, useEffect, useRef, useState } from "react";

interface TimelinePlayerProps {
  total: number;          // length T of the observation sequence
  value: number | null;   // current cursor (null = not playing)
  onChange: (t: number | null) => void;
}

const SPEEDS: { label: string; fps: number }[] = [
  { label: "0.5×", fps: 5 },
  { label: "1×", fps: 10 },
  { label: "2×", fps: 20 },
  { label: "4×", fps: 40 },
];

export function TimelinePlayer({ total, value, onChange }: TimelinePlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(1); // default 1×
  const tickRef = useRef<number | null>(null);

  const fps = SPEEDS[speedIdx].fps;

  // Animation loop
  useEffect(() => {
    if (!playing) {
      if (tickRef.current !== null) {
        window.clearInterval(tickRef.current);
        tickRef.current = null;
      }
      return;
    }
    const intervalMs = Math.max(20, 1000 / fps);
    tickRef.current = window.setInterval(() => {
      const cur = value ?? 0;
      const next = cur + 1;
      if (next >= total) {
        onChange(total - 1);
        setPlaying(false);
      } else {
        onChange(next);
      }
    }, intervalMs);
    return () => {
      if (tickRef.current !== null) {
        window.clearInterval(tickRef.current);
        tickRef.current = null;
      }
    };
  }, [playing, fps, value, total, onChange]);

  const btn =
    "px-2 py-1 rounded text-sm border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed";

  const handleStep = useCallback(
    (delta: number) => {
      const cur = value ?? 0;
      const next = Math.max(0, Math.min(total - 1, cur + delta));
      onChange(next);
    },
    [value, total, onChange],
  );

  const reset = useCallback(() => {
    setPlaying(false);
    onChange(null);
  }, [onChange]);

  return (
    <div className="border border-slate-200 rounded-md p-3 bg-white mb-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => {
            if (value === null) onChange(0);
            setPlaying((p) => !p);
          }}
          className={btn}
          title={playing ? "Pause" : "Play"}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <button
          type="button"
          onClick={() => handleStep(-1)}
          disabled={value === null}
          className={btn}
          title="Step back"
        >
          ◀
        </button>
        <button
          type="button"
          onClick={() => handleStep(1)}
          disabled={value === null}
          className={btn}
          title="Step forward"
        >
          ▶
        </button>
        <button
          type="button"
          onClick={reset}
          disabled={value === null}
          className={btn}
          title="Stop & reset"
        >
          ■ Stop
        </button>
        <div className="w-px h-6 bg-slate-300" />
        <div className="flex gap-0.5 bg-slate-100 rounded p-0.5">
          {SPEEDS.map((s, i) => (
            <button
              key={s.label}
              type="button"
              onClick={() => setSpeedIdx(i)}
              className={
                "px-2 py-0.5 text-xs rounded " +
                (i === speedIdx
                  ? "bg-brand-600 text-white"
                  : "text-slate-600 hover:bg-slate-200")
              }
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="w-px h-6 bg-slate-300" />
        <span className="text-xs font-mono text-slate-600 min-w-[80px]">
          t = {value === null ? "—" : value} / {total - 1}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={Math.max(0, total - 1)}
        value={value ?? 0}
        onChange={(e) => {
          onChange(parseInt(e.target.value, 10));
        }}
        className="w-full mt-3"
        disabled={total === 0}
      />
    </div>
  );
}
