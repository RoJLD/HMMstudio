import type { TopologyData, TopologyState } from "../store/topologyStore";
import { topologyToYAML, yamlToTopology } from "./yaml";

type TopologyPartial = Parameters<TopologyState["loadTopology"]>[0];

const URL_PARAM = "topology";

/** Compress a string to a URL-safe base64 payload. */
function encodeForUrl(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function decodeFromUrl(payload: string): string {
  let b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
  while (b64.length % 4 !== 0) b64 += "=";
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

/** Build a shareable URL for the current topology (relative to current location). */
export function buildShareUrl(state: TopologyData): string {
  const yamlText = topologyToYAML(state);
  const payload = encodeForUrl(yamlText);
  const url = new URL(window.location.href);
  url.searchParams.set(URL_PARAM, payload);
  return url.toString();
}

/** If the current URL has a `?topology=...` payload, parse and return it. */
export function readSharedTopology(): TopologyPartial | null {
  const params = new URLSearchParams(window.location.search);
  const payload = params.get(URL_PARAM);
  if (!payload) return null;
  try {
    const text = decodeFromUrl(payload);
    return yamlToTopology(text);
  } catch {
    return null;
  }
}

/** Remove the topology param from the URL without reloading. */
export function clearTopologyParam(): void {
  const url = new URL(window.location.href);
  if (!url.searchParams.has(URL_PARAM)) return;
  url.searchParams.delete(URL_PARAM);
  window.history.replaceState({}, "", url.toString());
}
