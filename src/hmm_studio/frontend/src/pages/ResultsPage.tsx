import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getFitStatus,
  getFitTransmat,
  getFitDecoded,
  getFitSeries,
  getFitEmissions,
  getFitConvergence,
  getNhmmInfo,
  listAnnotations,
  openFitProgressSocket,
  type AnnotationOut,
  type FitJobResult,
  type TransmatResponse,
  type DecodedResponse,
  type SeriesResponse,
  type EmissionsResponse,
  type NhmmInfoResponse,
} from "../api/client";
import { TransmatHeatmap } from "../components/results/TransmatHeatmap";
import { TransmatGraph } from "../components/results/TransmatGraph";
import { DataCurves } from "../components/results/DataCurves";
import { ViterbiTimeline } from "../components/results/ViterbiTimeline";
import { EmissionsPanel } from "../components/results/EmissionsPanel";
import { ProgressCurve } from "../components/results/ProgressCurve";
import { NhmmAtPanel } from "../components/results/NhmmAtPanel";
import { TimelinePlayer } from "../components/results/TimelinePlayer";

// The WS message includes a `progress` array not on FitJobResult
interface WsMessage extends FitJobResult {
  progress?: number[];
}

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [status, setStatus] = useState<FitJobResult | null>(null);
  const [progress, setProgress] = useState<number[]>([]);
  const [transmat, setTransmat] = useState<TransmatResponse | null>(null);
  const [decoded, setDecoded] = useState<DecodedResponse | null>(null);
  const [series, setSeries] = useState<SeriesResponse | null>(null);
  const [emissions, setEmissions] = useState<EmissionsResponse | null>(null);
  const [nhmmInfo, setNhmmInfo] = useState<NhmmInfoResponse | null>(null);
  const [convergence, setConvergence] = useState<number[] | null>(null);
  const [currentT, setCurrentT] = useState<number | null>(null);
  const [annotations, setAnnotations] = useState<AnnotationOut[]>([]);

  // Open WebSocket for live progress; also poll status via REST fallback.
  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    // Initial REST fetch
    getFitStatus(jobId).then((s) => {
      if (!cancelled) setStatus(s);
    });

    // Live WebSocket
    const ws = openFitProgressSocket(jobId, (msg) => {
      if (cancelled) return;
      const wsMsg = msg as WsMessage;
      setStatus(wsMsg);
      if (wsMsg.progress && wsMsg.progress.length > 0) {
        setProgress(wsMsg.progress);
      }
    });

    return () => {
      cancelled = true;
      ws.close();
    };
  }, [jobId]);

  // REST poll while running (backup for when WS is lagging or unavailable)
  useEffect(() => {
    if (!jobId) return;
    if (status?.status === "done" || status?.status === "failed") return;
    const handle = setInterval(async () => {
      try {
        const s = await getFitStatus(jobId);
        setStatus(s);
      } catch {
        // ignore transient errors
      }
    }, 800);
    return () => clearInterval(handle);
  }, [jobId, status?.status]);

  // When done, fetch transmat + decoded + emissions + nhmm_info in parallel.
  useEffect(() => {
    if (!jobId || status?.status !== "done") return;
    Promise.all([
      getFitTransmat(jobId).catch(() => null),
      getFitDecoded(jobId).catch(() => null),
      getFitEmissions(jobId).catch(() => null),
      getNhmmInfo(jobId).catch(() => null),
      getFitSeries(jobId).catch(() => null),
      getFitConvergence(jobId).catch(() => null),
    ]).then(([t, d, e, n, s, c]) => {
      setTransmat(t);
      setDecoded(d);
      setEmissions(e);
      setNhmmInfo(n);
      setSeries(s);
      setConvergence(c ? c.convergence_history : null);
    });
  }, [jobId, status?.status]);

  // Fetch annotations for the fit's dataset.
  useEffect(() => {
    if (!status?.dataset_id) {
      setAnnotations([]);
      return;
    }
    listAnnotations(status.dataset_id)
      .then((r) => setAnnotations(r.annotations))
      .catch(() => setAnnotations([]));
  }, [status?.dataset_id]);

  if (!status) {
    return (
      <div className="text-slate-600">
        Loading job <code>{jobId}</code>…
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-semibold text-slate-900 mb-1">
        Results{" "}
        <span className="text-sm font-mono text-slate-500">{jobId}</span>
      </h2>
      <p className="text-slate-600 mb-6">
        Status: <Badge status={status.status} />
      </p>

      {/* Metadata cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <Metric label="log-lik" value={fmt(status.log_likelihood)} />
        <Metric label="BIC" value={fmt(status.bic)} />
        <Metric label="AIC" value={fmt(status.aic)} />
        <Metric
          label="iters"
          value={status.n_iter_actual?.toString() ?? "—"}
        />
      </div>

      {status.error && (
        <p className="mt-2 mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {status.error}
        </p>
      )}

      {/* Live progress while running */}
      {(status.status === "running" || status.status === "queued") && (
        <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-2">
            Convergence (log-likelihood vs iteration)
          </h3>
          <ProgressCurve history={progress} />
          {progress.length === 0 && (
            <p className="text-xs text-slate-500 mt-2">
              Waiting for first iteration to report…
            </p>
          )}
        </div>
      )}

      {/* Done: full results */}
      {status.status === "done" && (
        <>
          {convergence && convergence.length > 1 && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-1">
                Convergence (log-likelihood vs iteration)
              </h3>
              <p className="text-xs text-slate-500 mb-3">
                The EM log-likelihood should climb and plateau. A flat-then-jump
                or non-monotone trace signals an initialization or numerical issue —
                re-fit with another seed.
              </p>
              <ProgressCurve history={convergence} />
            </div>
          )}
          {decoded && decoded.n_total > 0 && (
            <TimelinePlayer
              total={decoded.n_total}
              value={currentT}
              onChange={setCurrentT}
            />
          )}
          {transmat && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-1">
                Transition graph
              </h3>
              <p className="text-xs text-slate-500 mb-3">
                Arrows show direction; the bubble is the learned probability and
                thicker edges are more likely. A self-loop means staying in that regime.
                Press ▶ above to light up the current state, its posterior, and the active transition.
              </p>
              <TransmatGraph data={transmat} decoded={decoded} currentT={currentT} />
            </div>
          )}
          {transmat && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Transition matrix
              </h3>
              <TransmatHeatmap data={transmat} />
            </div>
          )}
          {decoded && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Viterbi path
              </h3>
              <ViterbiTimeline data={decoded} currentT={currentT} annotations={annotations} />
            </div>
          )}
          {series && series.columns.length > 0 && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Observed data
              </h3>
              <DataCurves data={series} currentT={currentT} />
            </div>
          )}
          {emissions && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Emissions
              </h3>
              <EmissionsPanel data={emissions} />
            </div>
          )}
          {nhmmInfo?.is_nhmm && (
            <div className="border border-slate-200 rounded-md p-4 bg-white mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Time-varying transitions A(t) (NHMM)
              </h3>
              <NhmmAtPanel jobId={jobId!} info={nhmmInfo} controlledT={currentT} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-slate-200 text-slate-800",
    running: "bg-blue-100 text-blue-800",
    done: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    cancelled: "bg-amber-100 text-amber-800",
  };
  return (
    <span
      className={
        "inline-block px-2 py-0.5 rounded text-xs font-medium " +
        (colors[status] ?? "bg-slate-200 text-slate-800")
      }
    >
      {status}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-slate-200 rounded-md p-3 bg-white">
      <div className="text-xs text-slate-500 uppercase">{label}</div>
      <div className="text-lg font-semibold text-slate-900 font-mono">
        {value}
      </div>
    </div>
  );
}

function fmt(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return v.toFixed(2);
}
