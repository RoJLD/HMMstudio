import type { DecodedResponse } from "../../api/client";
import { useSvgExport } from "../../hooks/useSvgExport";
import { ExportButton } from "../../hooks/ExportButton";

interface Props {
  data: DecodedResponse;
  currentT?: number | null;   // NEW: external cursor in full-T units
}

// Brand-friendly palette
const PALETTE = [
  "#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
  "#8b5cf6", "#ec4899", "#84cc16", "#f97316", "#0ea5e9",
];

export function ViterbiTimeline({ data, currentT }: Props) {
  const T = data.viterbi.length;
  const W = 900;
  const H = 60;
  const cellW = W / T;

  const { svgRef, exportSvg } = useSvgExport("viterbi");

  // Convert full-T cursor to downsampled coordinate
  const cursorTDs =
    currentT !== null && currentT !== undefined
      ? Math.floor(currentT / data.step)
      : null;
  const cursorX =
    cursorTDs !== null && cursorTDs >= 0 && cursorTDs < T
      ? cursorTDs * cellW + cellW / 2
      : null;

  return (
    <div>
      <div className="flex justify-end mb-1">
        <ExportButton onClick={() => exportSvg()} />
      </div>
      <svg ref={svgRef} width={W} height={H} className="block w-full">
        {data.viterbi.map((s, t) => (
          <rect
            key={t}
            x={t * cellW}
            y={0}
            width={cellW + 0.5}
            height={H}
            fill={PALETTE[s % PALETTE.length]}
          />
        ))}
        {cursorX !== null && (
          <line
            x1={cursorX}
            y1={0}
            x2={cursorX}
            y2={H}
            stroke="white"
            strokeWidth={2}
            strokeDasharray="3 3"
            pointerEvents="none"
          />
        )}
        {cursorX !== null && (
          <line
            x1={cursorX}
            y1={0}
            x2={cursorX}
            y2={H}
            stroke="black"
            strokeWidth={1}
            pointerEvents="none"
          />
        )}
      </svg>
      <div className="flex gap-3 flex-wrap mt-3 text-xs">
        {data.state_names.map((name, k) => (
          <div key={k} className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ background: PALETTE[k % PALETTE.length] }}
            />
            <span className="text-slate-700">{name}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500 mt-2">
        {data.n_total} observations
        {data.step > 1 ? `, downsampled by ${data.step}×` : ""}.
        {currentT !== null && currentT !== undefined && cursorTDs !== null && cursorTDs >= 0 && cursorTDs < T && (
          <span>
            {" "}Cursor: t={currentT}, state ={" "}
            <strong className="font-mono">
              {data.state_names[data.viterbi[cursorTDs]] ?? "?"}
            </strong>
          </span>
        )}
      </p>
    </div>
  );
}
