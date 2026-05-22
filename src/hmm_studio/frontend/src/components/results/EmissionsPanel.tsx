import type { EmissionsResponse } from "../../api/client";

interface Props {
  data: EmissionsResponse;
}

export function EmissionsPanel({ data }: Props) {
  const K = data.state_names.length;

  if (data.type === "gaussian" || data.type === "gmm") {
    const means = data.means ?? [];
    return (
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs border-collapse">
          <thead className="bg-slate-50">
            <tr>
              <th className="border border-slate-200 px-2 py-1 text-left font-medium">State</th>
              <th className="border border-slate-200 px-2 py-1 text-left font-medium">Mean</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: K }).map((_, k) => (
              <tr key={k}>
                <td className="border border-slate-200 px-2 py-1 font-mono">
                  {data.state_names[k]}
                </td>
                <td className="border border-slate-200 px-2 py-1 font-mono">
                  [{(means[k] ?? []).map((v: number) => v.toFixed(3)).join(", ")}]
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (data.type === "multinomial") {
    const ep = data.emissionprob ?? [];
    const n = ep[0]?.length ?? 0;
    return (
      <table className="min-w-full text-xs border-collapse">
        <thead className="bg-slate-50">
          <tr>
            <th className="border border-slate-200 px-2 py-1 text-left">State</th>
            {Array.from({ length: n }).map((_, j) => (
              <th key={j} className="border border-slate-200 px-2 py-1 text-left">
                P(sym{j})
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ep.map((row: number[], k: number) => (
            <tr key={k}>
              <td className="border border-slate-200 px-2 py-1 font-mono">
                {data.state_names[k]}
              </td>
              {row.map((v: number, j: number) => (
                <td key={j} className="border border-slate-200 px-2 py-1 font-mono">
                  {v.toFixed(3)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  if (data.type === "poisson") {
    const lambdas = data.lambdas ?? [];
    return (
      <table className="min-w-full text-xs border-collapse">
        <thead className="bg-slate-50">
          <tr>
            <th className="border border-slate-200 px-2 py-1 text-left">State</th>
            <th className="border border-slate-200 px-2 py-1 text-left">λ</th>
          </tr>
        </thead>
        <tbody>
          {lambdas.map((row: number[], k: number) => (
            <tr key={k}>
              <td className="border border-slate-200 px-2 py-1 font-mono">
                {data.state_names[k]}
              </td>
              <td className="border border-slate-200 px-2 py-1 font-mono">
                [{row.map((v: number) => v.toFixed(3)).join(", ")}]
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return <p className="text-xs text-slate-500">unsupported emission type</p>;
}
