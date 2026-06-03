import { BaseEdge, type EdgeProps } from "reactflow";

/** A self-transition (source===target) drawn as an arc looping above the node,
 *  so the transmat diagonal is visible and editable. */
export function SelfLoopEdge(p: EdgeProps) {
  const {
    sourceX,
    sourceY,
    targetX,
    targetY,
    markerEnd,
    style,
    label,
    labelStyle,
    labelBgStyle,
    labelBgPadding,
    labelBgBorderRadius,
  } = p;
  const topY = Math.min(sourceY, targetY) - 70;
  const path = `M ${sourceX} ${sourceY} C ${sourceX + 50} ${topY}, ${targetX - 50} ${topY}, ${targetX} ${targetY}`;
  const midX = (sourceX + targetX) / 2;
  return (
    <BaseEdge
      path={path}
      markerEnd={markerEnd}
      style={style}
      label={label}
      labelX={midX}
      labelY={topY + 12}
      labelStyle={labelStyle}
      labelShowBg
      labelBgStyle={labelBgStyle}
      labelBgPadding={labelBgPadding}
      labelBgBorderRadius={labelBgBorderRadius}
    />
  );
}
