import type { SeriesResponse } from "../../api/client";

const COLORS = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6"];

/** Line chart of the observed variables over time, synced to the timeline
 *  cursor. Each series is min–max normalized so shapes are comparable across
 *  variables on different scales. */
export function DataCurves({
  data,
  currentT,
}: {
  data: SeriesResponse;
  currentT?: number | null;
}) {
  const n = data.series[0]?.length ?? 0;
  if (n === 0) return null;

  const W = 900;
  const H = 150;
  const padX = 8;
  const padY = 10;
  const plotW = W - 2 * padX;
  const plotH = H - 2 * padY;
  const xAt = (i: number) => padX + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);

  const paths = data.series.map((s) => {
    let min = Infinity;
    let max = -Infinity;
    for (const v of s) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
    const range = max - min || 1;
    return s
      .map((v, i) => {
        const y = padY + plotH - ((v - min) / range) * plotH;
        return `${i === 0 ? "M" : "L"}${xAt(i).toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  });

  const cursorIdx =
    currentT != null && data.step > 0
      ? Math.min(n - 1, Math.max(0, Math.floor(currentT / data.step)))
      : null;
  const cursorX = cursorIdx != null ? xAt(cursorIdx) : null;

  return (
    <div>
      <svg width={W} height={H} className="block w-full">
        {paths.map((d, k) => (
          <path
            key={k}
            d={d}
            fill="none"
            stroke={COLORS[k % COLORS.length]}
            strokeWidth={1.5}
          />
        ))}
        {cursorX != null && (
          <line
            x1={cursorX}
            y1={0}
            x2={cursorX}
            y2={H}
            stroke="#0f172a"
            strokeWidth={1}
            strokeDasharray="3 3"
            pointerEvents="none"
          />
        )}
      </svg>
      <div className="flex gap-3 flex-wrap mt-2 text-xs">
        {data.columns.map((c, k) => (
          <div key={c} className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-0.5"
              style={{ background: COLORS[k % COLORS.length] }}
            />
            <span className="text-slate-700 font-mono">{c}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500 mt-1">
        {data.n_total} observations
        {data.step > 1 ? `, downsampled ${data.step}×` : ""}; each series min–max normalized.
      </p>
    </div>
  );
}
