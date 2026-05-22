import { useState } from "react";

const K = 3;
const STATE_NAMES = ["bear", "range", "bull"];

// Compute A(z) row by row via multinomial logit
// Each row uses a different set of logit offsets that respond to z
function transmatAt(z: number): number[][] {
  const A: number[][] = [];

  // Row 0 (bear state): as z increases, more likely to stay in bear or shift to range
  const row0 = [0, 0.4 + 0.5 * z, 0.1 + 1.0 * z];
  // Row 1 (range state): as z increases, range transitions more to bull
  const row1 = [-0.3 - 0.4 * z, 0, 0.2 + 0.6 * z];
  // Row 2 (bull state): as z decreases (negative), bull tends to revert
  const row2 = [-0.5 - 0.5 * z, -0.3 - 0.2 * z, 0];

  for (const logits of [row0, row1, row2]) {
    const e = logits.map((x) => Math.exp(x));
    const s = e[0] + e[1] + e[2];
    A.push(e.map((x) => x / s));
  }
  return A;
}

export function NhmmBreathing() {
  const [z, setZ] = useState(0);
  const A = transmatAt(z);
  const cellSize = 50;
  const labelSpace = 70;
  const W = labelSpace + K * cellSize + 20;
  const H = labelSpace + K * cellSize + 20;

  const colorFor = (v: number) => {
    const t = Math.min(1, Math.max(0, v));
    const r = Math.round(238 + (79 - 238) * t);
    const g = Math.round(242 + (70 - 242) * t);
    const b = Math.round(255 + (229 - 255) * t);
    return `rgb(${r},${g},${b})`;
  };

  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs text-slate-600 font-mono w-20">
          z = {z.toFixed(2)}
        </span>
        <input
          type="range"
          min={-2}
          max={2}
          step={0.1}
          value={z}
          onChange={(e) => setZ(parseFloat(e.target.value))}
          className="flex-1"
        />
      </div>
      <svg width={W} height={H} className="block mx-auto">
        {/* Column headers */}
        {STATE_NAMES.map((name, j) => (
          <text
            key={"colhdr-" + j}
            x={labelSpace + j * cellSize + cellSize / 2}
            y={labelSpace - 8}
            textAnchor="middle"
            className="text-xs fill-slate-600"
          >
            {name}
          </text>
        ))}
        {/* Row headers */}
        {STATE_NAMES.map((name, i) => (
          <text
            key={"rowhdr-" + i}
            x={labelSpace - 8}
            y={labelSpace + i * cellSize + cellSize / 2 + 4}
            textAnchor="end"
            className="text-xs fill-slate-600"
          >
            {name}
          </text>
        ))}
        {/* Cells */}
        {A.map((row, i) =>
          row.map((v, j) => (
            <g key={`${i}-${j}`} transform={`translate(${labelSpace + j * cellSize},${labelSpace + i * cellSize})`}>
              <rect width={cellSize} height={cellSize} fill={colorFor(v)} stroke="#fff" strokeWidth={1} />
              <text
                x={cellSize / 2}
                y={cellSize / 2 + 4}
                textAnchor="middle"
                className={"text-[10px] font-mono " + (v > 0.5 ? "fill-white" : "fill-slate-700")}
              >
                {v.toFixed(2)}
              </text>
            </g>
          )),
        )}
      </svg>
      <p className="text-xs text-slate-500 mt-2 text-center">
        Drag the slider: z controls regime-shift propensity. Each row is a softmax over learned beta coefficients.
      </p>
    </div>
  );
}
