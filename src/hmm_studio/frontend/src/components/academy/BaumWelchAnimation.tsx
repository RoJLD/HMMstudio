import { useEffect, useRef, useState } from "react";

// Pre-computed synthetic Baum-Welch trace: monotonically-increasing log-lik
// values that look like a real EM convergence.
const TRACE = [-2200, -1850, -1620, -1480, -1395, -1340, -1308, -1290, -1281, -1276, -1273, -1272, -1271.5];
const A_FRAMES: number[][][] = [
  // initial random-ish
  [
    [0.4, 0.4, 0.2],
    [0.3, 0.4, 0.3],
    [0.2, 0.3, 0.5],
  ],
  [
    [0.5, 0.35, 0.15],
    [0.25, 0.5, 0.25],
    [0.15, 0.3, 0.55],
  ],
  [
    [0.6, 0.3, 0.1],
    [0.2, 0.6, 0.2],
    [0.1, 0.3, 0.6],
  ],
  [
    [0.7, 0.25, 0.05],
    [0.15, 0.7, 0.15],
    [0.05, 0.3, 0.65],
  ],
  [
    [0.78, 0.18, 0.04],
    [0.1, 0.78, 0.12],
    [0.04, 0.26, 0.7],
  ],
  [
    [0.83, 0.13, 0.04],
    [0.08, 0.82, 0.1],
    [0.04, 0.24, 0.72],
  ],
  [
    [0.85, 0.12, 0.03],
    [0.07, 0.84, 0.09],
    [0.03, 0.23, 0.74],
  ],
];

export function BaumWelchAnimation() {
  const [iter, setIter] = useState(0);
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) {
      if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = window.setInterval(() => {
      setIter((i) => {
        const next = i + 1;
        if (next >= TRACE.length) {
          setPlaying(false);
          return TRACE.length - 1;
        }
        return next;
      });
    }, 500);
    return () => {
      if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
    };
  }, [playing]);

  // Plot the log-lik curve up to iter
  const W = 480;
  const H = 140;
  const padL = 50, padR = 10, padT = 10, padB = 24;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const lo = Math.min(...TRACE), hi = Math.max(...TRACE);
  const rng = hi - lo || 1;
  const points = TRACE.slice(0, iter + 1).map((v, i) => {
    const x = padL + (i / Math.max(1, TRACE.length - 1)) * innerW;
    const y = padT + (1 - (v - lo) / rng) * innerH;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  // A matrix to show (mod the available frames)
  const aFrame = A_FRAMES[Math.min(iter, A_FRAMES.length - 1)];

  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => {
            if (iter >= TRACE.length - 1) setIter(0);
            setPlaying((p) => !p);
          }}
          className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50"
        >
          {playing ? "Pause" : "Play"}
        </button>
        <button
          onClick={() => {
            setPlaying(false);
            setIter(0);
          }}
          className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50"
        >
          Reset
        </button>
        <span className="text-xs text-slate-600 font-mono ml-auto">
          iter = {iter} · log-lik = {TRACE[iter].toFixed(2)}
        </span>
      </div>

      <div className="flex gap-4 items-start">
        <div className="flex-1">
          <p className="text-xs text-slate-500 mb-1">Log-likelihood over EM iterations</p>
          <svg width={W} height={H} className="block">
            <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="#cbd5e1" />
            <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} stroke="#cbd5e1" />
            <polyline fill="none" stroke="#4f46e5" strokeWidth={2} points={points.join(" ")} />
            <text x={padL - 6} y={padT + 4} textAnchor="end" className="text-[10px] fill-slate-500">
              {hi.toFixed(0)}
            </text>
            <text x={padL - 6} y={padT + innerH} textAnchor="end" className="text-[10px] fill-slate-500">
              {lo.toFixed(0)}
            </text>
          </svg>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1">A matrix (snapshot)</p>
          <svg width={160} height={140} className="block">
            {aFrame.map((row, i) =>
              row.map((v, j) => {
                const t = Math.min(1, v);
                const r = Math.round(238 + (79 - 238) * t);
                const g = Math.round(242 + (70 - 242) * t);
                const b = Math.round(255 + (229 - 255) * t);
                return (
                  <g key={`${i}-${j}`} transform={`translate(${20 + j * 42},${10 + i * 42})`}>
                    <rect width={40} height={40} fill={`rgb(${r},${g},${b})`} stroke="#fff" strokeWidth={1} />
                    <text
                      x={20}
                      y={24}
                      textAnchor="middle"
                      className={"text-[10px] font-mono " + (v > 0.5 ? "fill-white" : "fill-slate-700")}
                    >
                      {v.toFixed(2)}
                    </text>
                  </g>
                );
              }),
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}
