import { DEFAULT_CONFIG, type AcademyConfig } from "./academy.config";

declare global {
  interface Window {
    __ACADEMY_CONFIG__?: Partial<AcademyConfig>;
  }
}

function read(): AcademyConfig {
  const w = (typeof window !== "undefined" && window.__ACADEMY_CONFIG__) || {};
  const env = import.meta.env as Record<string, string | undefined>;
  // `||` (not `??`) so empty strings injected by the Docker entrypoint fall
  // through to the next source / default.
  return {
    title: w.title || env.VITE_ACADEMY_TITLE || DEFAULT_CONFIG.title,
    studioUrl: w.studioUrl || env.VITE_STUDIO_URL || DEFAULT_CONFIG.studioUrl,
  };
}

const cfg = read();

export function getTitle(): string {
  return cfg.title;
}

export function getStudioUrl(): string {
  return cfg.studioUrl;
}
