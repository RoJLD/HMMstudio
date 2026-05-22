import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

// --- Geometry constants (module-level, stable) ---
const W = 320;
const H = 260;
const MARGIN = 30;
const SIDE = Math.min(W - 2 * MARGIN, H - 2 * MARGIN);
const CX = W / 2;
const CY = MARGIN + SIDE * 0.95;
const R = SIDE * 0.5;

// Triangle vertices: top (s0), bottom-right (s1), bottom-left (s2)
const VA: [number, number] = [CX, CY - R];
const VB: [number, number] = [CX + R * Math.sin((Math.PI * 2) / 3), CY + R * 0.5];
const VC: [number, number] = [CX - R * Math.sin((Math.PI * 2) / 3), CY + R * 0.5];

function baryToCart(bary: [number, number, number]): [number, number] {
  return [
    bary[0] * VA[0] + bary[1] * VB[0] + bary[2] * VC[0],
    bary[0] * VA[1] + bary[1] * VB[1] + bary[2] * VC[1],
  ];
}

function cartToBary(x: number, y: number): [number, number, number] {
  const v0x = VB[0] - VA[0], v0y = VB[1] - VA[1];
  const v1x = VC[0] - VA[0], v1y = VC[1] - VA[1];
  const v2x = x - VA[0], v2y = y - VA[1];
  const denom = v0x * v1y - v1x * v0y;
  const u = (v2x * v1y - v1x * v2y) / denom;
  const v = (v0x * v2y - v2x * v0y) / denom;
  const a = 1 - u - v;
  const clamped: [number, number, number] = [
    Math.max(0, a),
    Math.max(0, u),
    Math.max(0, v),
  ];
  const sum = clamped[0] + clamped[1] + clamped[2];
  return [clamped[0] / sum, clamped[1] / sum, clamped[2] / sum];
}

export function ProbabilitySimplex() {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [pos, setPos] = useState<[number, number, number]>([1 / 3, 1 / 3, 1 / 3]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Background triangle
    svg
      .append("polygon")
      .attr("points", `${VA[0]},${VA[1]} ${VB[0]},${VB[1]} ${VC[0]},${VC[1]}`)
      .attr("fill", "#f1f5f9")
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 2);

    // Vertex labels
    svg.append("text")
      .attr("x", VA[0]).attr("y", VA[1] - 10)
      .attr("text-anchor", "middle").attr("font-size", 12).attr("font-weight", "bold")
      .attr("fill", "#1e293b").text("→ s0 (prob 1)");
    svg.append("text")
      .attr("x", VB[0] + 5).attr("y", VB[1] + 18)
      .attr("text-anchor", "start").attr("font-size", 12).attr("font-weight", "bold")
      .attr("fill", "#1e293b").text("→ s1");
    svg.append("text")
      .attr("x", VC[0] - 5).attr("y", VC[1] + 18)
      .attr("text-anchor", "end").attr("font-size", 12).attr("font-weight", "bold")
      .attr("fill", "#1e293b").text("→ s2");

    // Draggable point
    const [px, py] = baryToCart(pos);
    const dragHandler = d3.drag<SVGCircleElement, unknown>().on("drag", (event) => {
      setPos(cartToBary(event.x, event.y));
    });
    svg
      .append("circle")
      .attr("cx", px).attr("cy", py).attr("r", 8)
      .attr("fill", "#4f46e5").attr("stroke", "white").attr("stroke-width", 2)
      .style("cursor", "grab")
      // d3 drag types require a Selection<GElement, ...>; casting to any is standard practice
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .call(dragHandler as any);
  }, [pos]);

  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <svg ref={svgRef} width={W} height={H} className="block mx-auto" />
      <div className="mt-3 text-xs font-mono text-slate-700 text-center">
        Row probs: [s0={pos[0].toFixed(3)}, s1={pos[1].toFixed(3)}, s2={pos[2].toFixed(3)}] · sum ={" "}
        <span className={Math.abs(pos[0] + pos[1] + pos[2] - 1) < 1e-6 ? "text-green-700" : "text-red-700"}>
          {(pos[0] + pos[1] + pos[2]).toFixed(3)}
        </span>
      </div>
    </div>
  );
}
