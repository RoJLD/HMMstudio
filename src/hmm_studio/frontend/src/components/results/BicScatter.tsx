interface BicScatterProps {
  data: { k: number; bic: number; aic: number }[];
  bestBic: number | null;
}

export function BicScatter({ data, bestBic }: BicScatterProps) {
  if (data.length === 0) {
    return <p className="text-xs text-slate-500">No completed fits yet.</p>;
  }
  const W = 700;
  const H = 240;
  const padL = 60,
    padR = 20,
    padT = 20,
    padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const ks = data.map((d) => d.k);
  const kMin = Math.min(...ks),
    kMax = Math.max(...ks);
  const allY = data.flatMap((d) => [d.bic, d.aic]);
  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const yRng = yMax - yMin || 1;

  const xOf = (k: number) =>
    padL + ((k - kMin) / Math.max(1, kMax - kMin)) * innerW;
  const yOf = (v: number) => padT + (1 - (v - yMin) / yRng) * innerH;

  const sorted = [...data].sort((a, b) => a.k - b.k);

  const bicPath = sorted
    .map((d, i) => (i === 0 ? "M" : "L") + ` ${xOf(d.k).toFixed(1)} ${yOf(d.bic).toFixed(1)}`)
    .join(" ");

  const aicPath = sorted
    .map((d, i) => (i === 0 ? "M" : "L") + ` ${xOf(d.k).toFixed(1)} ${yOf(d.aic).toFixed(1)}`)
    .join(" ");

  return (
    <div>
      <svg width={W} height={H} className="block w-full">
        {/* axes */}
        <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="#cbd5e1" />
        <line
          x1={padL}
          y1={padT + innerH}
          x2={padL + innerW}
          y2={padT + innerH}
          stroke="#cbd5e1"
        />
        {/* BIC line */}
        <path d={bicPath} stroke="#4f46e5" strokeWidth={2} fill="none" />
        {sorted.map((d) => (
          <circle
            key={"bic-" + d.k}
            cx={xOf(d.k)}
            cy={yOf(d.bic)}
            r={bestBic === d.k ? 7 : 4}
            fill={bestBic === d.k ? "#10b981" : "#4f46e5"}
          />
        ))}
        {/* AIC line */}
        <path d={aicPath} stroke="#f59e0b" strokeWidth={2} strokeDasharray="4 3" fill="none" />
        {sorted.map((d) => (
          <circle key={"aic-" + d.k} cx={xOf(d.k)} cy={yOf(d.aic)} r={3} fill="#f59e0b" />
        ))}
        {/* K labels */}
        {sorted.map((d) => (
          <text
            key={"klbl-" + d.k}
            x={xOf(d.k)}
            y={H - 8}
            textAnchor="middle"
            className="text-[10px] fill-slate-600"
          >
            {d.k}
          </text>
        ))}
        {/* y axis labels */}
        <text
          x={padL - 6}
          y={padT + 4}
          textAnchor="end"
          className="text-[10px] fill-slate-500"
        >
          {yMax.toFixed(0)}
        </text>
        <text
          x={padL - 6}
          y={padT + innerH}
          textAnchor="end"
          className="text-[10px] fill-slate-500"
        >
          {yMin.toFixed(0)}
        </text>
      </svg>
      <div className="flex gap-3 text-xs mt-1">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 bg-indigo-600" /> BIC
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 bg-amber-500" /> AIC
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full bg-green-500" /> Best by BIC
        </span>
      </div>
    </div>
  );
}
