import { useTopologyStore } from "../../store/topologyStore";

interface PerEdgePriorPanelProps {
  edgeId: string;
}

export function PerEdgePriorPanel({ edgeId }: PerEdgePriorPanelProps) {
  const edge = useTopologyStore((s) =>
    s.transitions.find((e) => e.id === edgeId),
  );
  const states = useTopologyStore((s) => s.states);
  const removeTransition = useTopologyStore((s) => s.removeTransition);
  const setEdgePriorWeight = useTopologyStore((s) => s.setEdgePriorWeight);
  const globalAlpha = useTopologyStore((s) => s.transmat_prior_alpha);

  if (!edge) {
    return (
      <div className="w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
        <p className="text-xs text-slate-500">
          Selected transition no longer exists.
        </p>
      </div>
    );
  }

  const srcName = states.find((s) => s.id === edge.source)?.name ?? edge.source;
  const tgtName = states.find((s) => s.id === edge.target)?.name ?? edge.target;
  const isOverride = edge.prior_weight !== undefined;

  return (
    <div className="w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
      <h2 className="text-sm font-semibold text-slate-900 mb-1">
        Transition: <span className="font-mono">{srcName}</span>{" "}
        <span className="text-slate-400">→</span>{" "}
        <span className="font-mono">{tgtName}</span>
      </h2>
      <p className="text-xs text-slate-500 mb-4 break-all">id: {edge.id}</p>

      <div className="mb-4">
        <h3 className="text-xs font-semibold uppercase text-slate-500 mb-2">
          Dirichlet prior weight
        </h3>
        <p className="text-xs text-slate-500 mb-2">
          Pseudo-count for this transition. Default = global α (
          <span className="font-mono">
            {globalAlpha !== null ? globalAlpha : "MLE"}
          </span>
          ). Higher values smooth this transition more strongly toward its
          row-average; lower values let the data dominate.
        </p>
        <div className="flex items-center gap-2">
          <input
            type="number"
            step={0.1}
            min={0}
            value={edge.prior_weight ?? globalAlpha ?? 1}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setEdgePriorWeight(
                edge.id,
                Number.isFinite(v) ? v : undefined,
              );
            }}
            className="border border-slate-300 rounded px-2 py-1 text-sm w-24 font-mono focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          />
          {isOverride && (
            <button
              type="button"
              onClick={() => setEdgePriorWeight(edge.id, undefined)}
              className="text-xs text-slate-500 hover:text-slate-700 underline"
            >
              clear override
            </button>
          )}
        </div>
        <p
          className={
            "text-xs mt-2 " +
            (isOverride ? "text-brand-700 font-medium" : "text-slate-400")
          }
        >
          {isOverride ? "● override active" : "○ using global α"}
        </p>
      </div>

      <div className="mt-6 pt-4 border-t border-slate-200">
        <button
          type="button"
          onClick={() => removeTransition(edge.id)}
          className="text-xs text-red-700 hover:text-red-900 hover:underline"
        >
          Delete this transition
        </button>
      </div>
    </div>
  );
}
