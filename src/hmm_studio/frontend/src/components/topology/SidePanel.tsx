import type {
  CovarianceType,
  EmissionType,
  InitSpec,
} from "../../store/topologyStore";
import { useTopologyStore } from "../../store/topologyStore";
import { PerStateEmissionPanel } from "./PerStateEmissionPanel";
import { PerEdgePriorPanel } from "./PerEdgePriorPanel";

interface SidePanelProps {
  validationError: string | null;
  validationSummary: string | null;
}

export function SidePanel({ validationError, validationSummary }: SidePanelProps) {
  const selectedStateId = useTopologyStore((s) => s.selectedStateId);
  const selectedEdgeId = useTopologyStore((s) => s.selectedEdgeId);

  if (selectedStateId) {
    return <PerStateEmissionPanel stateId={selectedStateId} />;
  }
  if (selectedEdgeId) {
    return <PerEdgePriorPanel edgeId={selectedEdgeId} />;
  }

  return <GlobalPanel validationError={validationError} validationSummary={validationSummary} />;
}

function GlobalPanel({ validationError, validationSummary }: SidePanelProps) {
  const name = useTopologyStore((s) => s.name);
  const setName = useTopologyStore((s) => s.setName);
  const emission = useTopologyStore((s) => s.emission);
  const setEmission = useTopologyStore((s) => s.setEmission);
  const init = useTopologyStore((s) => s.init);
  const setInit = useTopologyStore((s) => s.setInit);
  const fit = useTopologyStore((s) => s.fit);
  const setFit = useTopologyStore((s) => s.setFit);
  const transmat_prior_alpha = useTopologyStore((s) => s.transmat_prior_alpha);
  const setPriorAlpha = useTopologyStore((s) => s.setPriorAlpha);

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

  const Row = ({
    label,
    children,
  }: {
    label: string;
    children: React.ReactNode;
  }) => (
    <label className="flex items-center justify-between gap-2 text-sm">
      <span className="text-slate-700">{label}</span>
      {children}
    </label>
  );

  const inputCls =
    "border border-slate-300 rounded px-2 py-1 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-brand-500/40";

  return (
    <div className="w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
      <Section title="Model">
        <Row label="Name">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls}
          />
        </Row>
      </Section>

      <Section title="Emission">
        <Row label="Type">
          <select
            value={emission.type}
            onChange={(e) =>
              setEmission({
                ...emission,
                type: e.target.value as EmissionType,
              })
            }
            className={inputCls}
          >
            <option value="gaussian">gaussian</option>
            <option value="gmm">gmm</option>
            <option value="multinomial">multinomial</option>
            <option value="poisson">poisson</option>
          </select>
        </Row>
        {(emission.type === "gaussian" ||
          emission.type === "gmm" ||
          emission.type === "poisson") && (
          <Row label="n_features">
            <input
              type="number"
              min={1}
              value={emission.n_features ?? 1}
              onChange={(e) =>
                setEmission({
                  ...emission,
                  n_features: parseInt(e.target.value, 10),
                })
              }
              className={inputCls}
            />
          </Row>
        )}
        {(emission.type === "gaussian" || emission.type === "gmm") && (
          <Row label="covariance">
            <select
              value={emission.covariance_type ?? "full"}
              onChange={(e) =>
                setEmission({
                  ...emission,
                  covariance_type: e.target.value as CovarianceType,
                })
              }
              className={inputCls}
            >
              <option value="full">full</option>
              <option value="diag">diag</option>
              <option value="tied">tied</option>
              <option value="spherical">spherical</option>
            </select>
          </Row>
        )}
        {emission.type === "gmm" && (
          <Row label="n_mix">
            <input
              type="number"
              min={1}
              value={emission.n_mix ?? 2}
              onChange={(e) =>
                setEmission({
                  ...emission,
                  n_mix: parseInt(e.target.value, 10),
                })
              }
              className={inputCls}
            />
          </Row>
        )}
        {emission.type === "multinomial" && (
          <Row label="n_symbols">
            <input
              type="number"
              min={2}
              value={emission.n_symbols ?? 2}
              onChange={(e) =>
                setEmission({
                  ...emission,
                  n_symbols: parseInt(e.target.value, 10),
                })
              }
              className={inputCls}
            />
          </Row>
        )}
      </Section>

      <Section title="Init">
        <Row label="Strategy">
          <select
            value={init.strategy}
            onChange={(e) =>
              setInit({
                ...init,
                strategy: e.target.value as InitSpec["strategy"],
              })
            }
            className={inputCls}
          >
            <option value="uniform">uniform</option>
            <option value="random">random</option>
            <option value="kmeans">kmeans</option>
            <option value="data_frequencies">data_frequencies</option>
          </select>
        </Row>
        <Row label="Seed">
          <input
            type="number"
            value={init.seed}
            onChange={(e) =>
              setInit({ ...init, seed: parseInt(e.target.value, 10) })
            }
            className={inputCls}
          />
        </Row>
      </Section>

      <Section title="Fit">
        <Row label="n_iter">
          <input
            type="number"
            min={1}
            value={fit.n_iter}
            onChange={(e) =>
              setFit({ ...fit, n_iter: parseInt(e.target.value, 10) })
            }
            className={inputCls}
          />
        </Row>
        <Row label="tol">
          <input
            type="number"
            step={1e-5}
            value={fit.tol}
            onChange={(e) =>
              setFit({ ...fit, tol: parseFloat(e.target.value) })
            }
            className={inputCls}
          />
        </Row>
      </Section>

      <Section title="Priors (A.9)">
        <Row label="α (Dirichlet)">
          <input
            type="number"
            step={0.1}
            min={0}
            value={transmat_prior_alpha ?? ""}
            placeholder="(MLE)"
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              setPriorAlpha(Number.isFinite(v) ? v : null);
            }}
            className={inputCls}
          />
        </Row>
        <p className="text-xs text-slate-500">
          α &gt; 1 smooths toward uniform; α = 1 (or empty) = MLE. Select an
          individual transition for per-edge override.
        </p>
      </Section>

      <Section title="Validation">
        {validationError ? (
          <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1 break-words">
            {validationError}
          </p>
        ) : validationSummary ? (
          <p className="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">
            {validationSummary}
          </p>
        ) : (
          <p className="text-xs text-slate-500">…</p>
        )}
      </Section>
    </div>
  );
}
