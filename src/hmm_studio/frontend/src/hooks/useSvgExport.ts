import { useCallback, useRef } from "react";
import { downloadSvg } from "../lib/exportSvg";

/** Returns a ref to attach to an `<svg>` and a download handler.
 *
 * Usage:
 *   const { svgRef, exportSvg } = useSvgExport("my-figure");
 *   <svg ref={svgRef}>...</svg>
 *   <button onClick={() => exportSvg()}>Download SVG</button>
 */
export function useSvgExport(defaultFilename: string) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const exportSvg = useCallback(
    (filename?: string) => {
      if (!svgRef.current) return;
      downloadSvg(svgRef.current, filename ?? defaultFilename);
    },
    [defaultFilename],
  );
  return { svgRef, exportSvg };
}
