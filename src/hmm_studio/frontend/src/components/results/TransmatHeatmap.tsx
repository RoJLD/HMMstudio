import type { TransmatResponse } from "../../api/client";
import { useSvgExport } from "../../hooks/useSvgExport";
import { ExportButton } from "../../hooks/ExportButton";

interface Props {
  data: TransmatResponse;
}

export function TransmatHeatmap({ data }: Props) {
  const K = data.n_states;
  const cellSize = 50;
  const labelSpace = 70;
  const W = labelSpace + K * cellSize + 20;
  const H = labelSpace + K * cellSize + 20;

  const { svgRef, exportSvg } = useSvgExport("transmat");

  const colorFor = (v: number, allowed: boolean) => {
    if (!allowed) return "#e5e7eb"; // light gray for forbidden
    const t = Math.min(1, Math.max(0, v));
    // brand indigo scale
    const r = Math.round(238 + (79 - 238) * t);
    const g = Math.round(242 + (70 - 242) * t);
    const b = Math.round(255 + (229 - 255) * t);
    return `rgb(${r},${g},${b})`;
  };

  return (
    <div>
      <div className="flex justify-end mb-1">
        <ExportButton onClick={() => exportSvg()} />
      </div>
      <svg ref={svgRef} width={W} height={H} className="block">
        {/* Column headers */}
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
        {/* Row headers */}
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
        {/* Cells */}
        {data.transmat.map((row, i) =>
          row.map((v, j) => {
            const allowed = data.mask[i][j];
            return (
              <g
                key={`${i}-${j}`}
                transform={`translate(${labelSpace + j * cellSize},${
                  labelSpace + i * cellSize
                })`}
              >
                <rect
                  width={cellSize}
                  height={cellSize}
                  fill={colorFor(v, allowed)}
                  stroke="#fff"
                  strokeWidth={1}
                />
                <text
                  x={cellSize / 2}
                  y={cellSize / 2 + 4}
                  textAnchor="middle"
                  className={
                    "text-[10px] font-mono " +
                    (v > 0.5 ? "fill-white" : "fill-slate-700")
                  }
                >
                  {allowed ? v.toFixed(2) : "×"}
                </text>
              </g>
            );
          }),
        )}
      </svg>
    </div>
  );
}
