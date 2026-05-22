import { useState } from "react";

interface TrellisProps {
  mode: "forward" | "viterbi";
}

// Tiny fixed model for the demo
const STATES = ["s0", "s1"] as const;
const OBSERVATIONS = ["R", "B"] as const; // Red / Blue symbols
const T = 6;
const SEQ: (typeof OBSERVATIONS)[number][] = ["R", "R", "B", "R", "B", "B"];

const PI = [0.6, 0.4]; // initial state distribution
const A: number[][] = [
  [0.7, 0.3],
  [0.4, 0.6],
];
const B: Record<(typeof OBSERVATIONS)[number], number[]> = {
  R: [0.9, 0.2], // P(R | s0), P(R | s1)
  B: [0.1, 0.8],
};

function computeForward(): number[][] {
  // alpha[t][k] = P(o_1..o_t, z_t=k)
  const alpha: number[][] = Array.from({ length: T }, () => [0, 0]);
  for (let k = 0; k < 2; k++) {
    alpha[0][k] = PI[k] * B[SEQ[0]][k];
  }
  for (let t = 1; t < T; t++) {
    for (let k = 0; k < 2; k++) {
      alpha[t][k] = B[SEQ[t]][k] * (alpha[t - 1][0] * A[0][k] + alpha[t - 1][1] * A[1][k]);
    }
  }
  return alpha;
}

function computeViterbi(): { delta: number[][]; backtrace: number[][]; path: number[] } {
  const delta: number[][] = Array.from({ length: T }, () => [0, 0]);
  const psi: number[][] = Array.from({ length: T }, () => [0, 0]);
  for (let k = 0; k < 2; k++) {
    delta[0][k] = PI[k] * B[SEQ[0]][k];
  }
  for (let t = 1; t < T; t++) {
    for (let k = 0; k < 2; k++) {
      let best = -Infinity;
      let argmax = 0;
      for (let i = 0; i < 2; i++) {
        const v = delta[t - 1][i] * A[i][k];
        if (v > best) {
          best = v;
          argmax = i;
        }
      }
      delta[t][k] = B[SEQ[t]][k] * best;
      psi[t][k] = argmax;
    }
  }
  // Backtrace
  const path: number[] = new Array(T).fill(0);
  path[T - 1] = delta[T - 1][0] > delta[T - 1][1] ? 0 : 1;
  for (let t = T - 2; t >= 0; t--) {
    path[t] = psi[t + 1][path[t + 1]];
  }
  return { delta, backtrace: psi, path };
}

export function Trellis({ mode }: TrellisProps) {
  const [step, setStep] = useState(0);
  const values = mode === "forward" ? computeForward() : computeViterbi().delta;
  const path = mode === "viterbi" ? computeViterbi().path : null;

  const cellW = 60;
  const cellH = 50;
  const padL = 60;
  const padT = 40;
  const W = padL + T * cellW + 20;
  const H = padT + 2 * cellH + 60;

  const fmt = (v: number) => (v < 0.0001 ? "0" : v.toFixed(4));

  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-40"
        >
          ◀ Back
        </button>
        <button
          onClick={() => setStep((s) => Math.min(T - 1, s + 1))}
          disabled={step >= T - 1}
          className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-40"
        >
          Step ▶
        </button>
        <button
          onClick={() => setStep(0)}
          className="px-3 py-1 text-sm rounded border border-slate-300 hover:bg-slate-50"
        >
          ⟲ Reset
        </button>
        <span className="text-xs text-slate-600 font-mono ml-auto">
          t = {step} · obs = {SEQ[step]}
        </span>
      </div>

      <svg width={W} height={H} className="block mx-auto">
        {/* Observation row */}
        <text x={padL - 8} y={padT - 18} textAnchor="end" className="text-xs fill-slate-500 font-mono">
          obs
        </text>
        {SEQ.map((o, t) => (
          <text
            key={"obs-" + t}
            x={padL + t * cellW + cellW / 2}
            y={padT - 18}
            textAnchor="middle"
            className={
              "text-xs font-mono " + (t === step ? "fill-brand-600 font-bold" : "fill-slate-500")
            }
          >
            {o}
          </text>
        ))}

        {/* State labels */}
        {STATES.map((s, k) => (
          <text
            key={"st-" + k}
            x={padL - 8}
            y={padT + k * cellH + cellH / 2 + 4}
            textAnchor="end"
            className="text-xs fill-slate-700 font-mono"
          >
            {s}
          </text>
        ))}

        {/* Cells */}
        {values.map((row, t) =>
          row.map((v, k) => {
            const filled = t <= step;
            const isOnPath = mode === "viterbi" && path && path[t] === k && filled;
            return (
              <g key={`${t}-${k}`}>
                <rect
                  x={padL + t * cellW}
                  y={padT + k * cellH}
                  width={cellW - 2}
                  height={cellH - 2}
                  fill={isOnPath ? "#dcfce7" : filled ? "#eef2ff" : "#f8fafc"}
                  stroke={isOnPath ? "#16a34a" : "#cbd5e1"}
                  strokeWidth={isOnPath ? 2 : 1}
                />
                <text
                  x={padL + t * cellW + cellW / 2 - 1}
                  y={padT + k * cellH + cellH / 2 + 4}
                  textAnchor="middle"
                  className={"text-[10px] font-mono " + (filled ? "fill-slate-800" : "fill-slate-300")}
                >
                  {filled ? fmt(v) : "·"}
                </text>
              </g>
            );
          }),
        )}

        {/* Footer label */}
        <text x={padL} y={H - 8} className="text-xs fill-slate-500">
          {mode === "forward"
            ? "alpha_t(k) = P(o_1..o_t, z_t=k) — sum over predecessor states"
            : "delta_t(k) = max P(z_1..z_t, o_1..o_t) — max over predecessor; green = backtrace"}
        </text>
      </svg>

      <p className="text-xs text-slate-600 mt-3 font-mono">
        Final P(O | model) = {fmt(values[T - 1][0] + values[T - 1][1])}{" "}
        {mode === "viterbi" && (
          <>
            · Most likely path: {path?.map((k) => STATES[k]).join(" -&gt; ")}
          </>
        )}
      </p>
    </div>
  );
}
