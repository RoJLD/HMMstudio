import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

const STATES = ["sunny", "cloudy", "rainy"] as const;
type State = (typeof STATES)[number];

const STATE_COLORS: Record<State, string> = {
  sunny: "#facc15",
  cloudy: "#94a3b8",
  rainy: "#60a5fa",
};

// Transition matrix
const A: Record<State, Record<State, number>> = {
  sunny: { sunny: 0.7, cloudy: 0.25, rainy: 0.05 },
  cloudy: { sunny: 0.3, cloudy: 0.4, rainy: 0.3 },
  rainy: { sunny: 0.1, cloudy: 0.4, rainy: 0.5 },
};

export function MarkovChainDemo() {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [current, setCurrent] = useState<State>("sunny");
  const [history, setHistory] = useState<State[]>(["sunny"]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    const W = 360;
    const H = 220;
    const cx = W / 2;
    const cy = H / 2 + 10;
    const r = 80;

    const positions: Record<State, [number, number]> = {
      sunny: [cx, cy - r],
      cloudy: [cx + r * Math.sin((Math.PI * 2) / 3), cy + r * 0.5],
      rainy: [cx - r * Math.sin((Math.PI * 2) / 3), cy + r * 0.5],
    };

    // Edges
    STATES.forEach((from) => {
      STATES.forEach((to) => {
        if (A[from][to] < 0.05) return;
        const [x1, y1] = positions[from];
        const [x2, y2] = positions[to];
        if (from === to) {
          // Self-loop
          svg
            .append("path")
            .attr(
              "d",
              `M ${x1 - 10} ${y1 - 25} C ${x1 - 30} ${y1 - 55}, ${x1 + 30} ${y1 - 55}, ${x1 + 10} ${y1 - 25}`,
            )
            .attr("fill", "none")
            .attr("stroke", "#cbd5e1")
            .attr("stroke-width", A[from][to] * 4 + 0.5);
        } else {
          svg
            .append("line")
            .attr("x1", x1)
            .attr("y1", y1)
            .attr("x2", x2)
            .attr("y2", y2)
            .attr("stroke", "#cbd5e1")
            .attr("stroke-width", A[from][to] * 4 + 0.5);
        }
      });
    });

    // Nodes
    STATES.forEach((s) => {
      const [x, y] = positions[s];
      const isCurrent = s === current;
      svg
        .append("circle")
        .attr("cx", x)
        .attr("cy", y)
        .attr("r", isCurrent ? 26 : 22)
        .attr("fill", STATE_COLORS[s])
        .attr("stroke", isCurrent ? "#1e293b" : "#cbd5e1")
        .attr("stroke-width", isCurrent ? 3 : 1);
      svg
        .append("text")
        .attr("x", x)
        .attr("y", y + 4)
        .attr("text-anchor", "middle")
        .attr("font-size", 11)
        .attr("font-family", "monospace")
        .attr("fill", "#1e293b")
        .text(s);
    });
  }, [current]);

  function step() {
    const probs = A[current];
    const r = Math.random();
    let acc = 0;
    for (const s of STATES) {
      acc += probs[s];
      if (r < acc) {
        setCurrent(s);
        setHistory((h) => [...h.slice(-19), s]);
        return;
      }
    }
  }

  function reset() {
    setCurrent("sunny");
    setHistory(["sunny"]);
  }

  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <svg ref={svgRef} width={360} height={220} className="block mx-auto" />
      <div className="flex gap-2 justify-center mt-3">
        <button
          type="button"
          onClick={step}
          className="px-4 py-1.5 rounded text-sm bg-brand-600 text-white hover:bg-brand-700"
        >
          ▶ Step
        </button>
        <button
          type="button"
          onClick={reset}
          className="px-4 py-1.5 rounded text-sm border border-slate-300 hover:bg-slate-50"
        >
          ⟲ Reset
        </button>
      </div>
      <div className="mt-3 text-xs text-slate-600 text-center">
        Trajectory:{" "}
        <span className="font-mono">{history.join(" → ")}</span>
      </div>
    </div>
  );
}
