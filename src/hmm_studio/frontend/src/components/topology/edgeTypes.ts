import type { EdgeTypes } from "reactflow";
import { SelfLoopEdge } from "./edges/SelfLoopEdge";
import { CurvedEdge } from "./edges/CurvedEdge";

export const edgeTypes: EdgeTypes = {
  selfLoop: SelfLoopEdge,
  curved: CurvedEdge,
};
