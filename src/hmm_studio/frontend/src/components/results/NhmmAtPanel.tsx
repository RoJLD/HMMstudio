import { useEffect, useState } from "react";
import { getAAt, type AAtResponse, type NhmmInfoResponse } from "../../api/client";

interface NhmmAtPanelProps {
  jobId: string;
  info: NhmmInfoResponse;
}

export function NhmmAtPanel({ jobId, info }: NhmmAtPanelProps) {
  const T = info.T ?? 0;
  const K = info.n_states ?? 0;
  const [t, setT] = useState(0);
  const [a, setA] = useState<AAtResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAAt(jobId, t).then((r) => {
      if (!cancelled) setA(r);
    });
    return () => {
      cancelled = true;
    };
  }, [jobId, t]);

  if (T === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs text-slate-600 font-mono">
          t = {t} / {T - 1}
        </span>
        <input
          type="range"
          min={0}
          max={Math.max(0, T - 1)}
          value={t}
          onChange={(e) => setT(parseInt(e.target.value, 10))}
          className="flex-1"
        />
      </div>
      {a && <Heatmap data={a} K={K} />}
      <p className="text-xs text-slate-500 mt-2">
        Covariates: {(info.covariate_names ?? []).join(", ")}
      </p>
    </div>
  );
}

function Heatmap({ data, K }: { data: AAtResponse; K: number }) {
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
    <svg width={W} height={H} className="block">
      {data.state_names.map((name, j) => (
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
      {data.state_names.map((name, i) => (
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
      {data.A.map((row, i) =>
        row.map((v, j) => (
          <g
            key={`${i}-${j}`}
            transform={`translate(${labelSpace + j * cellSize},${labelSpace + i * cellSize})`}
          >
            <rect
              width={cellSize}
              height={cellSize}
              fill={colorFor(v)}
              stroke="#fff"
              strokeWidth={1}
            />
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
  );
}
