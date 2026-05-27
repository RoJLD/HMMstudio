import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Single source of truth for the app version: package.json. The footer reads
// the injected __APP_VERSION__, so bumping the package version at release time
// updates the UI automatically (no second place to edit).
const pkg = JSON.parse(
  readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf-8"),
) as { version: string };

// Manual chunk splitting strategy:
//   - react-vendor: react + react-dom + react-router-dom (core runtime, rarely changes)
//   - reactflow: the topology editor's graph library (large, used only on /topology)
//   - d3: D3 (used only by Academy demos)
//   - zustand: state management (small but shared across pages)
//   - default: the app code (everything else)
//
// Rationale: keep the per-route delta small. When the user visits /topology
// they pay for reactflow; on /academy they pay for d3; etc. The browser
// caches each chunk separately, so subsequent visits hit cache.
function manualChunks(id: string): string | undefined {
  if (id.includes("node_modules")) {
    if (
      id.includes("react-dom") ||
      id.includes("/react/") ||
      id.includes("react-router-dom") ||
      id.includes("scheduler")
    ) {
      return "react-vendor";
    }
    if (id.includes("reactflow") || id.includes("@reactflow") || id.includes("d3-")) {
      // Note: reactflow internally depends on d3-* sub-packages. Bundling them
      // together avoids cross-chunk imports.
      return "reactflow";
    }
    if (id.includes("/d3/") || id.endsWith("/d3")) {
      // Standalone d3 (the academy uses it directly)
      return "d3";
    }
    if (id.includes("zustand") || id.includes("zundo")) {
      return "state";
    }
    if (id.includes("js-yaml")) {
      return "yaml";
    }
  }
  return undefined; // fall into the default app chunk
}

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
      "/health": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
    // Raise the chunk size warning ceiling since we deliberately have
    // a 140 KB reactflow chunk — that's intentional.
    chunkSizeWarningLimit: 250,
  },
});
