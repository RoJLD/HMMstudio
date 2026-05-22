// Typed API client wrapping the FastAPI backend.

export interface HealthResponse {
  status: string;
}

export interface TopologyValidateResponse {
  valid: boolean;
  error: string | null;
  summary: string | null;
}

export interface DatasetPreview {
  id: string;
  filename: string;
  n_rows: number;
  n_cols: number;
  columns: string[];
  dtypes: Record<string, string>;
  head: Array<Record<string, unknown>>;
}

export interface FitJobResult {
  id: string;
  status: string;
  log_likelihood: number | null;
  bic: number | null;
  aic: number | null;
  n_iter_actual: number | null;
  converged: boolean | null;
  result_path: string | null;
  error: string | null;
}

const BASE = ""; // same-origin; Vite dev proxy routes /api → backend.

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, init);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`HTTP ${r.status}: ${text}`);
  }
  return (await r.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return jsonFetch<HealthResponse>("/health");
}

export async function validateTopology(
  yaml_content: string,
): Promise<TopologyValidateResponse> {
  return jsonFetch<TopologyValidateResponse>("/api/topology/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_content }),
  });
}

export async function uploadDataset(file: File): Promise<DatasetPreview> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(BASE + "/api/data/upload", {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    throw new Error(`upload failed: ${r.status} ${await r.text()}`);
  }
  return (await r.json()) as DatasetPreview;
}

export async function startFit(params: {
  topology_yaml: string;
  dataset_id: string;
  seed?: number;
}): Promise<FitJobResult> {
  return jsonFetch<FitJobResult>("/api/fit/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getFitStatus(jobId: string): Promise<FitJobResult> {
  return jsonFetch<FitJobResult>(`/api/fit/${jobId}`);
}

export function openFitProgressSocket(
  jobId: string,
  onMessage: (msg: FitJobResult) => void,
): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${window.location.host}/ws/fit/${jobId}`);
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data as string);
      onMessage(data as FitJobResult);
    } catch {
      // ignore non-JSON frames
    }
  };
  return ws;
}
