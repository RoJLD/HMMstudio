interface Props {
  history: number[];
}

export function ProgressCurve({ history }: Props) {
  if (history.length === 0) {
    return <div className="h-32" />;
  }
  const W = 800;
  const H = 120;
  const padL = 50, padR = 10, padT = 10, padB = 24;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const lo = Math.min(...history);
  const hi = Math.max(...history);
  const rng = hi - lo || 1;

  const pts = history.map((v, i) => {
    const x = padL + (i / Math.max(1, history.length - 1)) * innerW;
    const y = padT + (1 - (v - lo) / rng) * innerH;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg width={W} height={H} className="block w-full">
      <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="#cbd5e1" />
      <line
        x1={padL}
        y1={padT + innerH}
        x2={padL + innerW}
        y2={padT + innerH}
        stroke="#cbd5e1"
      />
      <polyline
        fill="none"
        stroke="#4f46e5"
        strokeWidth={2}
        points={pts.join(" ")}
      />
      <text x={padL - 6} y={padT + 4} textAnchor="end" className="text-[10px] fill-slate-500">
        {hi.toFixed(0)}
      </text>
      <text
        x={padL - 6}
        y={padT + innerH}
        textAnchor="end"
        className="text-[10px] fill-slate-500"
      >
        {lo.toFixed(0)}
      </text>
      <text
        x={padL + innerW / 2}
        y={H - 6}
        textAnchor="middle"
        className="text-[10px] fill-slate-500"
      >
        iteration ({history.length})
      </text>
    </svg>
  );
}
