const ERGODIC_A = [
  [0.5, 0.3, 0.2],
  [0.25, 0.5, 0.25],
  [0.2, 0.3, 0.5],
];
const LEFT_RIGHT_A = [
  [0.7, 0.3, 0.0],
  [0.0, 0.6, 0.4],
  [0.0, 0.0, 1.0],
];

function MiniHeatmap({ A, label }: { A: number[][]; label: string }) {
  return (
    <div>
      <p className="text-xs font-semibold text-slate-700 text-center mb-1">{label}</p>
      <svg width={140} height={140} className="block mx-auto">
        {A.map((row, i) =>
          row.map((v, j) => {
            const t = Math.min(1, v);
            const r = Math.round(238 + (79 - 238) * t);
            const g = Math.round(242 + (70 - 242) * t);
            const b = Math.round(255 + (229 - 255) * t);
            const allowed = v > 0;
            return (
              <g key={`${i}-${j}`} transform={`translate(${20 + j * 36},${10 + i * 36})`}>
                <rect
                  width={34}
                  height={34}
                  fill={allowed ? `rgb(${r},${g},${b})` : "#e5e7eb"}
                  stroke="#fff"
                  strokeWidth={1}
                />
                <text
                  x={17}
                  y={20}
                  textAnchor="middle"
                  className={"text-[10px] font-mono " + (v > 0.5 ? "fill-white" : "fill-slate-700")}
                >
                  {allowed ? v.toFixed(2) : "x"}
                </text>
              </g>
            );
          }),
        )}
      </svg>
    </div>
  );
}

export function TopologyComparison() {
  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <MiniHeatmap A={ERGODIC_A} label="Ergodic (all edges allowed)" />
        <MiniHeatmap A={LEFT_RIGHT_A} label="Left-right (Bakis)" />
      </div>
      <p className="text-xs text-slate-500 mt-3 text-center">
        Forbidden edges (gray x) stay exactly zero through
        every M-step. hmm-studio enforces this via a binary mask
        multiplied after each Baum-Welch update.
      </p>
    </div>
  );
}
