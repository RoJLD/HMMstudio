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
  hqic: number | null;
  n_iter_actual: number | null;
  converged: boolean | null;
  result_path: string | null;
  error: string | null;
  dataset_id: string | null;
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
  covariate_names?: string[];
  lengths?: number[];
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

export interface TransmatResponse {
  state_names: string[];
  transmat: number[][];
  mask: boolean[][];
  n_states: number;
}

export interface DecodedResponse {
  viterbi: number[];
  posterior: number[][];
  n_total: number;
  step: number;
  state_names: string[];
}

export interface EmissionsResponse {
  type: "gaussian" | "gmm" | "multinomial" | "poisson";
  state_names: string[];
  means?: number[][];
  covars?: number[][][];
  emissionprob?: number[][];
  lambdas?: number[][];
}

export async function getFitTransmat(jobId: string): Promise<TransmatResponse> {
  return jsonFetch<TransmatResponse>(`/api/fit/${jobId}/transmat`);
}

export async function getFitDecoded(jobId: string): Promise<DecodedResponse> {
  return jsonFetch<DecodedResponse>(`/api/fit/${jobId}/decoded`);
}

export async function getFitEmissions(jobId: string): Promise<EmissionsResponse> {
  return jsonFetch<EmissionsResponse>(`/api/fit/${jobId}/emissions`);
}

export interface NhmmInfoResponse {
  is_nhmm: boolean;
  T?: number;
  n_states?: number;
  covariate_names?: string[];
  state_names?: string[];
  reason?: string;
}

export interface AAtResponse {
  t: number;
  T: number;
  A: number[][];
  state_names: string[];
  covariate_names: string[];
}

export async function getNhmmInfo(jobId: string): Promise<NhmmInfoResponse> {
  return jsonFetch<NhmmInfoResponse>(`/api/fit/${jobId}/nhmm_info`);
}

export async function getAAt(jobId: string, t: number): Promise<AAtResponse> {
  return jsonFetch<AAtResponse>(`/api/fit/${jobId}/A_at?t=${t}`);
}

export interface ScanChildStatus {
  job_id: string;
  k: number;
  status: string;
  log_likelihood: number | null;
  bic: number | null;
  aic: number | null;
  hqic: number | null;
  converged: boolean | null;
  n_iter_actual: number | null;
  error: string | null;
}

export interface ScanResult {
  parent_id: string;
  k_min: number;
  k_max: number;
  overall_status: string;
  children: ScanChildStatus[];
  best_k_by_bic: number | null;
  best_k_by_aic: number | null;
  best_k_by_hqic: number | null;
}

export async function startScan(params: {
  topology_yaml: string;
  dataset_id: string;
  k_min: number;
  k_max: number;
  seed?: number;
  covariate_names?: string[];
  lengths?: number[];
}): Promise<{ parent_id: string }> {
  return jsonFetch<{ parent_id: string }>("/api/fit/scan/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getScan(parentId: string): Promise<ScanResult> {
  return jsonFetch<ScanResult>(`/api/fit/scan/${parentId}`);
}

export interface CompareChildStatus {
  job_id: string;
  label: string;
  emission: string;
  k: number;
  n_mix: number | null;
  status: string;
  log_likelihood: number | null;
  bic: number | null;
  aic: number | null;
  hqic: number | null;
  converged: boolean | null;
  n_iter_actual: number | null;
  error: string | null;
}

export interface CompareResult {
  parent_id: string;
  overall_status: string;
  children: CompareChildStatus[];
  best_label_by_bic: string | null;
  best_label_by_aic: string | null;
  best_label_by_hqic: string | null;
}

export async function startCompare(params: {
  topology_yaml: string;
  dataset_id: string;
  k_min: number;
  k_max: number;
  emission_types: string[];
  n_mix?: number;
  seed?: number;
  lengths?: number[];
}): Promise<{ parent_id: string }> {
  return jsonFetch<{ parent_id: string }>("/api/fit/compare/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getCompare(parentId: string): Promise<CompareResult> {
  return jsonFetch<CompareResult>(`/api/fit/compare/${parentId}`);
}

export interface AnnotationOut {
  id: string;
  dataset_id: string;
  t: number;
  label: string;
  color: string | null;
}

export interface AnnotationsResponse {
  dataset_id: string;
  annotations: AnnotationOut[];
}

export async function listAnnotations(datasetId: string): Promise<AnnotationsResponse> {
  return jsonFetch<AnnotationsResponse>(`/api/data/${datasetId}/annotations`);
}

export async function uploadAnnotations(
  datasetId: string,
  file: File,
): Promise<AnnotationsResponse> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(`/api/data/${datasetId}/annotations/upload`, {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    throw new Error(`annotation upload failed: ${r.status} ${await r.text()}`);
  }
  return (await r.json()) as AnnotationsResponse;
}

export async function deleteAnnotation(
  datasetId: string,
  annotationId: string,
): Promise<void> {
  const r = await fetch(`/api/data/${datasetId}/annotations/${annotationId}`, {
    method: "DELETE",
  });
  if (!r.ok) throw new Error(`delete failed: ${r.status}`);
}

// ---------------------------------------------------------------------------
// Warehouse (Phase B.10)
// ---------------------------------------------------------------------------

export interface WarehouseEntry {
  rel_path: string;
  size_bytes: number;
  modified_at: string; // ISO 8601
  format: string;
  has_sidecar: boolean;
}

export interface WarehouseList {
  warehouse_path: string;
  entries: WarehouseEntry[];
}

export interface WarehousePreview {
  rel_path: string;
  n_rows_total: number;
  n_cols: number;
  columns: string[];
  dtypes: Record<string, string>;
  head: Array<Record<string, unknown>>;
}

export interface WarehouseSidecarMeta {
  schema_version?: number;
  name?: string;
  description?: string;
  notes?: string;
  provenance?: Record<string, unknown>;
  columns?: Array<Record<string, unknown>>;
  extra?: Record<string, unknown>;
}

/**
 * Encode each segment of a relative path with encodeURIComponent while
 * preserving the `/` separators. Required so rel_paths like
 * ``archive/btc 2024.csv`` survive a round-trip through the URL.
 */
function encodeRelPath(relPath: string): string {
  return relPath.split("/").map(encodeURIComponent).join("/");
}

export async function listWarehouse(): Promise<WarehouseList> {
  return jsonFetch<WarehouseList>("/api/warehouse");
}

export async function refreshWarehouse(): Promise<WarehouseList> {
  return jsonFetch<WarehouseList>("/api/warehouse/refresh", { method: "POST" });
}

export async function getWarehousePreview(
  relPath: string,
  n = 10,
): Promise<WarehousePreview> {
  return jsonFetch<WarehousePreview>(
    `/api/warehouse/${encodeRelPath(relPath)}/preview?n=${n}`,
  );
}

export async function getWarehouseMeta(
  relPath: string,
): Promise<{ rel_path: string; sidecar: WarehouseSidecarMeta | null }> {
  return jsonFetch<{ rel_path: string; sidecar: WarehouseSidecarMeta | null }>(
    `/api/warehouse/${encodeRelPath(relPath)}/meta`,
  );
}

export async function putWarehouseMeta(
  relPath: string,
  meta: WarehouseSidecarMeta,
): Promise<{ rel_path: string; sidecar_written: boolean }> {
  return jsonFetch<{ rel_path: string; sidecar_written: boolean }>(
    `/api/warehouse/${encodeRelPath(relPath)}/meta`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(meta),
    },
  );
}

export async function uploadToWarehouse(
  file: File,
  subdir?: string,
): Promise<{ rel_path: string; size_bytes: number }> {
  const form = new FormData();
  form.append("file", file);
  if (subdir) form.append("subdir", subdir);
  const r = await fetch(BASE + "/api/warehouse/upload", {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    throw new Error(`upload to warehouse failed: ${r.status} ${await r.text()}`);
  }
  return (await r.json()) as { rel_path: string; size_bytes: number };
}

export async function promoteWarehouseDataset(
  relPath: string,
): Promise<DatasetPreview> {
  return jsonFetch<DatasetPreview>(
    `/api/warehouse/${encodeRelPath(relPath)}/promote`,
    { method: "POST" },
  );
}

// ---------------------------------------------------------------------------
// Settings (Phase B.10 §7)
// ---------------------------------------------------------------------------

export type SettingsSource = "db" | "env" | "unset";

export interface Settings {
  warehouse_path: string | null;
  warehouse_path_source: SettingsSource;
  warehouse_path_env: string | null;
  updated_at: string | null;
}

export async function getSettings(): Promise<Settings> {
  return jsonFetch<Settings>("/api/settings");
}

/**
 * Update user settings. Pass ``warehouse_path: ""`` or ``null`` to clear
 * the DB override (falls back to env / unset).
 */
export async function updateSettings(payload: {
  warehouse_path?: string | null;
}): Promise<Settings> {
  return jsonFetch<Settings>("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
