import { BaseEdge, type EdgeProps } from "reactflow";

/** A bidirectional transition: bow the edge perpendicular to the source→target
 *  line so A→B and B→A don't overlap. `data.dir` (+1/-1) picks the side. */
export function CurvedEdge(p: EdgeProps) {
  const {
    sourceX,
    sourceY,
    targetX,
    targetY,
    markerEnd,
    style,
    data,
    label,
    labelStyle,
    labelBgStyle,
    labelBgPadding,
    labelBgBorderRadius,
  } = p;
  const dir = (data?.dir ?? 1) as number;
  const mx = (sourceX + targetX) / 2;
  const my = (sourceY + targetY) / 2;
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const len = Math.hypot(dx, dy) || 1;
  const off = 45 * dir;
  const cx = mx + (-dy / len) * off;
  const cy = my + (dx / len) * off;
  const path = `M ${sourceX} ${sourceY} Q ${cx} ${cy} ${targetX} ${targetY}`;
  return (
    <BaseEdge
      path={path}
      markerEnd={markerEnd}
      style={style}
      label={label}
      labelX={cx}
      labelY={cy}
      labelStyle={labelStyle}
      labelShowBg
      labelBgStyle={labelBgStyle}
      labelBgPadding={labelBgPadding}
      labelBgBorderRadius={labelBgBorderRadius}
    />
  );
}
