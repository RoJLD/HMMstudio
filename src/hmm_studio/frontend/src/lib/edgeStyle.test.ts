import { describe, it, expect } from "vitest";
import { MarkerType } from "reactflow";
import { probEdgeStyle } from "./edgeStyle";

describe("probEdgeStyle", () => {
  it("scales strokeWidth as 1 + 5p", () => {
    expect(probEdgeStyle(0).style.strokeWidth).toBe(1);
    expect(probEdgeStyle(0.5).style.strokeWidth).toBe(3.5);
    expect(probEdgeStyle(1).style.strokeWidth).toBe(6);
  });

  it("labels with 2 decimals and uses a closed arrow", () => {
    const s = probEdgeStyle(0.42);
    expect(s.label).toBe("0.42");
    expect(s.markerEnd.type).toBe(MarkerType.ArrowClosed);
  });

  it("encodes p in the stroke opacity", () => {
    expect(probEdgeStyle(1).style.stroke).toBe("rgba(79,70,229,1.00)");
    expect(probEdgeStyle(0).style.stroke).toBe("rgba(79,70,229,0.30)");
  });
});
