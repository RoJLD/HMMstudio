import { useTopologyStore } from "../../store/topologyStore";

interface PerStateEmissionPanelProps {
  stateId: string;
}

export function PerStateEmissionPanel({ stateId }: PerStateEmissionPanelProps) {
  const state = useTopologyStore((s) =>
    s.states.find((n) => n.id === stateId),
  );
  const emission = useTopologyStore((s) => s.emission);
  const setStateInit = useTopologyStore((s) => s.setStateInit);
  const renameState = useTopologyStore((s) => s.renameState);
  const removeState = useTopologyStore((s) => s.removeState);

  if (!state) {
    return (
      <p className="text-xs text-slate-500">
        Selected state no longer exists.
      </p>
    );
  }

  const Section = ({
    title,
    children,
  }: {
    title: string;
    children: React.ReactNode;
  }) => (
    <div className="mb-4">
      <h3 className="text-xs font-semibold uppercase text-slate-500 mb-2">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );

  const inputCls =
    "border border-slate-300 rounded px-2 py-1 text-sm w-full focus:outline-none focus:ring-2 focus:ring-brand-500/40 font-mono";

  // Render init editor based on global emission type
  const renderInitEditor = () => {
    if (emission.type === "gaussian" || emission.type === "gmm") {
      const n = emission.n_features ?? 1;
      const current = state.init_mean ?? Array(n).fill(0);
      return (
        <Section title="Init mean">
          <p className="text-xs text-slate-500">
            Optional prior for this state's mean ({n} values).
          </p>
          <VectorInput
            value={current}
            length={n}
            onChange={(v) => setStateInit(state.id, "init_mean", v)}
            onClear={() => setStateInit(state.id, "init_mean", undefined)}
            isSet={state.init_mean !== undefined}
          />
        </Section>
      );
    }
    if (emission.type === "poisson") {
      const n = emission.n_features ?? 1;
      const current = state.init_lambda ?? Array(n).fill(1);
      return (
        <Section title="Init lambda">
          <p className="text-xs text-slate-500">
            Optional prior for this state's Poisson rate ({n} values, &gt; 0).
          </p>
          <VectorInput
            value={current}
            length={n}
            onChange={(v) =>
              setStateInit(
                state.id,
                "init_lambda",
                v.map((x) => Math.max(1e-6, x)),
              )
            }
            onClear={() => setStateInit(state.id, "init_lambda", undefined)}
            isSet={state.init_lambda !== undefined}
          />
        </Section>
      );
    }
    if (emission.type === "multinomial") {
      const n = emission.n_symbols ?? 2;
      const current = state.init_emissionprob ?? Array(n).fill(1 / n);
      return (
        <Section title="Init emission probabilities">
          <p className="text-xs text-slate-500">
            Optional prior for this state's symbol distribution ({n} values,
            normalized on save).
          </p>
          <VectorInput
            value={current}
            length={n}
            onChange={(v) => {
              const sum = v.reduce((a, b) => a + Math.max(0, b), 0);
              const normalized =
                sum > 0 ? v.map((x) => Math.max(0, x) / sum) : v;
              setStateInit(state.id, "init_emissionprob", normalized);
            }}
            onClear={() =>
              setStateInit(state.id, "init_emissionprob", undefined)
            }
            isSet={state.init_emissionprob !== undefined}
          />
        </Section>
      );
    }
    return (
      <p className="text-xs text-slate-500">
        No per-state init editor for emission type "{emission.type}".
      </p>
    );
  };

  return (
    <div className="w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-sm font-semibold text-slate-900">
          State: <span className="font-mono">{state.name}</span>
        </h2>
      </div>
      <p className="text-xs text-slate-500 mb-4 break-all">id: {state.id}</p>

      <Section title="Identity">
        <input
          value={state.name}
          onChange={(e) => renameState(state.id, e.target.value)}
          className={inputCls}
        />
      </Section>

      {renderInitEditor()}

      <div className="mt-6 pt-4 border-t border-slate-200">
        <button
          type="button"
          onClick={() => removeState(state.id)}
          className="text-xs text-red-700 hover:text-red-900 hover:underline"
        >
          Delete this state
        </button>
      </div>
    </div>
  );
}

interface VectorInputProps {
  value: number[];
  length: number;
  onChange: (v: number[]) => void;
  onClear: () => void;
  isSet: boolean;
}

function VectorInput({
  value,
  length,
  onChange,
  onClear,
  isSet,
}: VectorInputProps) {
  // Pad/truncate value to match length
  const v: number[] = Array.from(
    { length },
    (_, i) => value[i] ?? (i < value.length ? value[i] : 0),
  );

  return (
    <div>
      <div className="grid grid-cols-2 gap-1 mb-1">
        {v.map((x, i) => (
          <input
            key={i}
            type="number"
            step="any"
            value={x}
            onChange={(e) => {
              const parsed = parseFloat(e.target.value);
              const next = [...v];
              next[i] = Number.isFinite(parsed) ? parsed : 0;
              onChange(next);
            }}
            className="border border-slate-300 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          />
        ))}
      </div>
      <div className="flex items-center justify-between text-xs mt-1">
        <span
          className={
            isSet ? "text-brand-700 font-medium" : "text-slate-400"
          }
        >
          {isSet ? "● override active" : "○ using global init"}
        </span>
        {isSet && (
          <button
            type="button"
            onClick={onClear}
            className="text-slate-500 hover:text-slate-700 underline"
          >
            clear override
          </button>
        )}
      </div>
    </div>
  );
}
