import type { AnnotationOut, DecodedResponse } from "../../api/client";
import { useSvgExport } from "../../hooks/useSvgExport";
import { ExportButton } from "../../hooks/ExportButton";

interface Props {
  data: DecodedResponse;
  currentT?: number | null;   // external cursor in full-T units
  annotations?: AnnotationOut[];
}

// Brand-friendly palette
const PALETTE = [
  "#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
  "#8b5cf6", "#ec4899", "#84cc16", "#f97316", "#0ea5e9",
];

export function ViterbiTimeline({ data, currentT, annotations }: Props) {
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
        {annotations && annotations.length > 0 && annotations.map((a) => {
          // Map t (full-T scale) into downsampled svg coordinates
          const tDs = Math.floor(a.t / data.step);
          if (tDs < 0 || tDs >= T) return null;
          const x = tDs * cellW + cellW / 2;
          const color = a.color || "#ef4444";
          return (
            <g key={a.id} pointerEvents="none">
              <line
                x1={x}
                y1={0}
                x2={x}
                y2={H}
                stroke={color}
                strokeWidth={1.5}
                strokeDasharray="2 2"
                opacity={0.85}
              />
            </g>
          );
        })}
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
      {annotations && annotations.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-semibold text-slate-500 mb-1">Annotations</p>
          <div className="flex gap-3 flex-wrap text-xs">
            {annotations.slice(0, 8).map((a) => (
              <div key={a.id} className="flex items-center gap-1.5">
                <span
                  className="inline-block w-3 h-0.5"
                  style={{ background: a.color || "#ef4444" }}
                />
                <span className="text-slate-700 font-mono">t={a.t}</span>
                <span className="text-slate-600 truncate max-w-[120px]">{a.label}</span>
              </div>
            ))}
            {annotations.length > 8 && (
              <span className="text-slate-500">+{annotations.length - 8} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
