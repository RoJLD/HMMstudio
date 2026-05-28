# HMM Academy Standalone & Template — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained `academy/` directory on branch `academy-standalone` that builds the HMM Academy as a static, Docker-deployable app AND serves as a reusable template, by copying the existing Academy slice 1:1 and turning the only studio coupling (the "Try in editor" bridge) into a configurable external link.

**Architecture:** A new minimal Vite + React + Tailwind app under `academy/`. The Academy slice (`components/academy/`, `lessons/`, `store/academyStore.ts`, `ThemeToggle`, `useTheme`, `AcademyPage`, `LessonPage`, `index.css`) is copied **1:1 with its directory layout preserved** so every internal relative import keeps working. The standalone **keeps the `/academy` route prefix** so `AcademyPage`, `LessonCard` and `LessonPage` nav links need zero edits — only the bridge in `LessonPage` is replaced by `<TryInStudioLink>`. Runtime config (`window.__ACADEMY_CONFIG__`) is injected by an nginx entrypoint so the studio URL is changeable without a rebuild.

**Tech Stack:** Vite 5, React 18, react-router-dom 6, D3 7, zustand 4, TailwindCSS 3, TypeScript 5, nginx:alpine, Playwright (smoke).

> **Commit policy (project rule):** Per `CLAUDE.md`, commits require **explicit user approval**. Each task ends with an intended commit command — at execution time, pause and ask the user before running it. Never use `--no-verify`.

---

## Source-of-truth file map (what gets copied 1:1)

From `src/hmm_studio/frontend/src/` → `academy/src/` (identical relative paths):

- `components/academy/` — 16 files (BaumWelchAnimation, Flashcard, FurtherReading, LessonAssessment, LessonCard, LessonContent, MarkovChainDemo, NhmmBreathing, NotebookLink, ProbabilitySimplex, QuizRunner, StudyDeck, TopologyComparison, Trellis, lessonQuiz.ts, scoreQuiz.ts)
- `lessons/` — 15 files (lesson-1..14 + index.ts)
- `store/academyStore.ts`
- `components/ThemeToggle.tsx`
- `hooks/useTheme.ts`
- `pages/AcademyPage.tsx` (copied verbatim — keeps `/academy` links)
- `pages/LessonPage.tsx` (copied, then **patched**: bridge → `<TryInStudioLink>`)
- `index.css`
- `vite-env.d.ts`

New framework/config files authored from scratch (see tasks): `main.tsx`, `App.tsx`, `Layout.tsx`, `runtimeConfig.ts`, `academy.config.ts`, `components/TryInStudioLink.tsx`, plus root configs + Docker + README + sync script + CI.

**Verification rationale:** the copied content is already exercised by the studio's own E2E suite. This plan's gates are: (a) `tsc` typecheck (catches broken imports / unused locals — `noUnusedLocals` is on), (b) `vite build`, (c) a Docker build + `curl` proving runtime config injection, (d) a Playwright smoke proving the index lists lessons, a lesson renders, and the studio button is hidden when `STUDIO_URL` is empty. Unit TDD is not used because the work is a verified 1:1 copy plus declarative config.

---

### Task 1: Branch + root scaffold (configs only, no app code yet)

**Files:**
- Create branch: `academy-standalone`
- Create: `academy/package.json`, `academy/vite.config.ts`, `academy/tailwind.config.js`, `academy/postcss.config.js`, `academy/tsconfig.json`, `academy/tsconfig.node.json`, `academy/index.html`, `academy/public/config.js`, `academy/.gitignore`

- [ ] **Step 1: Create the branch from current main**

Run:
```bash
cd /c/Users/robla/VScode_Project/HMMstudio
git checkout -b academy-standalone
mkdir -p academy/public academy/src academy/scripts academy/e2e
```
Expected: switched to a new branch `academy-standalone`.

- [ ] **Step 2: Write `academy/package.json`**

```json
{
  "name": "hmm-academy",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview --port 4173",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "d3": "^7.9.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "zustand": "^4.5.5"
  },
  "devDependencies": {
    "@types/d3": "^7.4.3",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.41",
    "tailwindcss": "^3.4.10",
    "typescript": "^5.5.4",
    "vite": "^5.4.2"
  }
}
```
Note: `js-yaml`, `reactflow`, `zundo` are intentionally dropped — the slice's only use of `js-yaml` was the bridge, and reactflow/zundo belong to the topology editor.

- [ ] **Step 3: Write `academy/vite.config.ts`**

```ts
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Single source of truth for the app version: package.json. The sidebar footer
// reads the injected __APP_VERSION__.
const pkg = JSON.parse(
  readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf-8"),
) as { version: string };

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
```

- [ ] **Step 4: Write `academy/tailwind.config.js`** (copy of studio's, content path scoped to this app)

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef2ff",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 5: Write `academy/postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Write `academy/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 7: Write `academy/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 8: Write `academy/index.html`** (loads `/config.js` BEFORE the app bundle)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HMM Academy</title>
    <script src="/config.js"></script>
  </head>
  <body class="bg-slate-50">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 9: Write `academy/public/config.js`** (committed dev/default fallback; overwritten at runtime in Docker)

```js
// Default runtime config. In production this file is regenerated by
// docker-entrypoint.sh from environment variables. Empty studioUrl => the
// "Open in HMM Studio" button is hidden (pure static learning mode).
window.__ACADEMY_CONFIG__ = {
  studioUrl: "",
  title: "HMM Academy",
};
```

- [ ] **Step 10: Write `academy/.gitignore`**

```
node_modules/
dist/
e2e/node_modules/
e2e/test-results/
e2e/playwright-report/
```

- [ ] **Step 11: Commit** (pause for user approval per commit policy)

```bash
git add academy/package.json academy/vite.config.ts academy/tailwind.config.js academy/postcss.config.js academy/tsconfig.json academy/tsconfig.node.json academy/index.html academy/public/config.js academy/.gitignore
git commit -m "feat(academy): scaffold standalone Vite app configs"
```

---

### Task 2: Copy the Academy slice 1:1

**Files:**
- Create (by copy): `academy/src/components/academy/*` (16), `academy/src/lessons/*` (15), `academy/src/store/academyStore.ts`, `academy/src/components/ThemeToggle.tsx`, `academy/src/hooks/useTheme.ts`, `academy/src/pages/AcademyPage.tsx`, `academy/src/pages/LessonPage.tsx`, `academy/src/index.css`, `academy/src/vite-env.d.ts`

- [ ] **Step 1: Copy the slice preserving directory layout**

Run:
```bash
cd /c/Users/robla/VScode_Project/HMMstudio
SRC=src/hmm_studio/frontend/src
DST=academy/src
mkdir -p "$DST/components/academy" "$DST/lessons" "$DST/store" "$DST/hooks" "$DST/pages"
cp "$SRC"/components/academy/*.ts "$SRC"/components/academy/*.tsx "$DST/components/academy/"
cp "$SRC"/lessons/*.ts "$SRC"/lessons/*.tsx "$DST/lessons/"
cp "$SRC/store/academyStore.ts" "$DST/store/academyStore.ts"
cp "$SRC/components/ThemeToggle.tsx" "$DST/components/ThemeToggle.tsx"
cp "$SRC/hooks/useTheme.ts" "$DST/hooks/useTheme.ts"
cp "$SRC/pages/AcademyPage.tsx" "$DST/pages/AcademyPage.tsx"
cp "$SRC/pages/LessonPage.tsx" "$DST/pages/LessonPage.tsx"
cp "$SRC/index.css" "$DST/index.css"
cp "$SRC/vite-env.d.ts" "$DST/vite-env.d.ts"
```

- [ ] **Step 2: Verify the copy counts and the only cross-slice import**

Run:
```bash
echo -n "academy components: " && ls academy/src/components/academy | wc -l   # expect 16
echo -n "lessons: " && ls academy/src/lessons | wc -l                          # expect 15
grep -rn "from \"\.\./store/topologyStore\|from \"\.\./lib/yaml\|reactflow\|zundo\|js-yaml" academy/src || echo "no foreign deps (expected: only LessonPage.tsx still references topologyStore/lib/yaml, fixed in Task 4)"
```
Expected: 16 and 15; the only matches are in `academy/src/pages/LessonPage.tsx` (lines importing `topologyStore` and `lib/yaml`) — these are removed in Task 4.

- [ ] **Step 3: Commit** (pause for approval)

```bash
git add academy/src
git commit -m "feat(academy): copy Academy slice 1:1 (lessons, components, store, theme)"
```

---

### Task 3: Runtime config + branding defaults

**Files:**
- Create: `academy/src/academy.config.ts`, `academy/src/runtimeConfig.ts`

- [ ] **Step 1: Write `academy/src/academy.config.ts`** (the template branding knobs)

```ts
// Branding / wiring defaults for this Academy instance.
//
// TEMPLATE NOTE: to repurpose this app for a different academy, replace the
// `src/lessons/` directory with your own lessons and edit the values below.
// Everything else (renderer, quiz engine, store, layout) is framework code you
// should not need to touch.

export interface AcademyConfig {
  /** Title shown in the sidebar / browser. */
  title: string;
  /**
   * Base URL of a full HMM Studio deployment. When set, lessons that ship a
   * topology preset show an "Open in HMM Studio" link pointing at
   * `${studioUrl}/topology`. Empty string => link hidden (pure static mode).
   */
  studioUrl: string;
}

export const DEFAULT_CONFIG: AcademyConfig = {
  title: "HMM Academy",
  studioUrl: "",
};
```

- [ ] **Step 2: Write `academy/src/runtimeConfig.ts`** (window global → env → defaults, evaluated once)

```ts
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
```

- [ ] **Step 3: Commit** (pause for approval)

```bash
git add academy/src/academy.config.ts academy/src/runtimeConfig.ts
git commit -m "feat(academy): runtime config (window global -> env -> defaults)"
```

---

### Task 4: Replace the bridge with `<TryInStudioLink>`

**Files:**
- Create: `academy/src/components/TryInStudioLink.tsx`
- Modify: `academy/src/pages/LessonPage.tsx`

- [ ] **Step 1: Write `academy/src/components/TryInStudioLink.tsx`**

```tsx
import { getStudioUrl } from "../runtimeConfig";

interface TryInStudioLinkProps {
  /** The lesson's topology preset YAML (presence drives whether to show). */
  yaml?: string;
}

/**
 * Standalone replacement for the studio's in-app "Try in editor" bridge.
 * Renders an external link to a configured HMM Studio deployment, or nothing
 * when no studio URL is configured (pure static learning mode).
 */
export function TryInStudioLink({ yaml }: TryInStudioLinkProps) {
  const studioUrl = getStudioUrl();
  if (!yaml || !studioUrl) return null;
  const href = `${studioUrl.replace(/\/+$/, "")}/topology`;
  return (
    <div className="mb-6 flex items-center gap-3">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="px-3 py-1.5 rounded text-sm bg-brand-600 text-white hover:bg-brand-700"
      >
        ↗ Open in HMM Studio
      </a>
      <span className="text-xs text-slate-500">
        Opens the topology editor in the full studio.
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Patch `academy/src/pages/LessonPage.tsx` — replace the import line 1**

Old (line 1):
```tsx
import { Link, useNavigate, useParams } from "react-router-dom";
```
New:
```tsx
import { Link, useParams } from "react-router-dom";
```
(`useNavigate` is no longer used — `noUnusedLocals` would otherwise fail the build.)

- [ ] **Step 3: Patch `LessonPage.tsx` — remove the bridge imports (old lines 6-7)**

Delete these two lines entirely:
```tsx
import { useTopologyStore } from "../store/topologyStore";
import { yamlToTopology } from "../lib/yaml";
```
Add this import alongside the other component imports (near the top, after the `NotebookLink` import):
```tsx
import { TryInStudioLink } from "../components/TryInStudioLink";
```

- [ ] **Step 4: Patch `LessonPage.tsx` — remove `navigate` and `handleTryInEditor`**

Delete the line inside the component:
```tsx
  const navigate = useNavigate();
```
Delete the whole function:
```tsx
  function handleTryInEditor() {
    if (!lesson?.presetTopologyYaml) return;
    try {
      const partial = yamlToTopology(lesson.presetTopologyYaml);
      useTopologyStore.getState().loadTopology(partial);
      navigate("/topology");
    } catch {
      // Silently fail — the user can still copy/paste
    }
  }
```

- [ ] **Step 5: Patch `LessonPage.tsx` — replace the button JSX block**

Old block:
```tsx
      {lesson.presetTopologyYaml && (
        <div className="mb-6 flex items-center gap-3">
          <button
            type="button"
            onClick={handleTryInEditor}
            className="px-3 py-1.5 rounded text-sm bg-brand-600 text-white hover:bg-brand-700"
          >
            ↗ Try in editor
          </button>
          <span className="text-xs text-slate-500">
            Loads the lesson topology into the visual editor.
          </span>
        </div>
      )}
```
New block:
```tsx
      <TryInStudioLink yaml={lesson.presetTopologyYaml} />
```

- [ ] **Step 6: Verify no foreign references remain**

Run:
```bash
grep -rn "topologyStore\|lib/yaml\|useNavigate\|handleTryInEditor" academy/src/pages/LessonPage.tsx || echo "clean"
```
Expected: `clean`.

- [ ] **Step 7: Commit** (pause for approval)

```bash
git add academy/src/components/TryInStudioLink.tsx academy/src/pages/LessonPage.tsx
git commit -m "feat(academy): link-out bridge -> TryInStudioLink (removes studio coupling)"
```

---

### Task 5: App shell (main, App router, Layout)

**Files:**
- Create: `academy/src/main.tsx`, `academy/src/App.tsx`, `academy/src/Layout.tsx`

- [ ] **Step 1: Write `academy/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 2: Write `academy/src/App.tsx`** (keeps `/academy` prefix; `/` redirects to it)

```tsx
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import AcademyPage from "./pages/AcademyPage";
import LessonPage from "./pages/LessonPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/academy" replace />} />
        <Route path="academy" element={<AcademyPage />} />
        <Route path="academy/:lessonId" element={<LessonPage />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 3: Write `academy/src/Layout.tsx`** (Academy-only shell)

```tsx
import { Link, Outlet, useLocation } from "react-router-dom";
import { ThemeToggle } from "./components/ThemeToggle";
import { getTitle } from "./runtimeConfig";

export default function Layout() {
  const location = useLocation();
  const onIndex =
    location.pathname === "/academy" || location.pathname === "/";

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-slate-900 text-slate-100 p-4 flex flex-col gap-2">
        <Link to="/academy" className="text-lg font-semibold mb-4">
          {getTitle()}
        </Link>
        <nav className="flex flex-col gap-1">
          <Link
            to="/academy"
            className={
              "px-3 py-2 rounded text-sm " +
              (onIndex
                ? "bg-brand-600 text-white"
                : "text-slate-300 hover:bg-slate-800 hover:text-white")
            }
          >
            All lessons
          </Link>
        </nav>
        <div className="mt-auto">
          <div className="mb-2">
            <ThemeToggle />
          </div>
          <div className="text-xs text-slate-500">v{__APP_VERSION__}</div>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto dark:bg-slate-900 dark:text-slate-200">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Commit** (pause for approval)

```bash
git add academy/src/main.tsx academy/src/App.tsx academy/src/Layout.tsx
git commit -m "feat(academy): app shell (router keeps /academy prefix, slim layout)"
```

---

### Task 6: Install, typecheck, build (verification gate)

**Files:** none created; this gates the copy + patches.

- [ ] **Step 1: Install dependencies**

Run:
```bash
cd /c/Users/robla/VScode_Project/HMMstudio/academy
npm install
```
Expected: lockfile created, no peer-dependency errors that abort install.

- [ ] **Step 2: Typecheck**

Run:
```bash
npm run lint
```
Expected: PASS (no errors). Common failure: an unused import left in `LessonPage.tsx` → re-check Task 4 steps 2-4. Another possible failure: a lesson importing something only present in the studio — if so, the import will name a missing module; resolve by copying that file into the slice (and add it to `scripts/sync-from-studio.sh` in Task 9).

- [ ] **Step 3: Build**

Run:
```bash
npm run build
```
Expected: `dist/` produced, including `dist/config.js` (copied from `public/`) and `dist/index.html`.

- [ ] **Step 4: Smoke the dev/preview server manually (optional sanity)**

Run:
```bash
npm run preview
```
Open `http://localhost:4173/academy` → the lesson index renders with category sections. Ctrl-C to stop.

- [ ] **Step 5: Commit the lockfile** (pause for approval)

```bash
git add academy/package-lock.json
git commit -m "chore(academy): add package-lock after first install"
```

---

### Task 7: Docker (static nginx + runtime config injection)

**Files:**
- Create: `academy/Dockerfile`, `academy/nginx.conf`, `academy/docker-entrypoint.sh`, `academy/.dockerignore`

- [ ] **Step 1: Write `academy/nginx.conf`** (SPA fallback so deep links like `/academy/lesson-2-markov-chains` work)

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

- [ ] **Step 2: Write `academy/docker-entrypoint.sh`** (regenerates config.js from env at container start)

```sh
#!/bin/sh
set -e
cat > /usr/share/nginx/html/config.js <<EOF
window.__ACADEMY_CONFIG__ = {
  studioUrl: "${STUDIO_URL:-}",
  title: "${ACADEMY_TITLE:-HMM Academy}"
};
EOF
```

- [ ] **Step 3: Write `academy/.dockerignore`**

```
node_modules
dist
e2e
.git
*.md
```

- [ ] **Step 4: Write `academy/Dockerfile`** (multi-stage; entrypoint dropped into nginx's `/docker-entrypoint.d/`)

```dockerfile
# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# nginx:alpine runs every executable in /docker-entrypoint.d/ before starting.
COPY docker-entrypoint.sh /docker-entrypoint.d/40-academy-config.sh
RUN chmod +x /docker-entrypoint.d/40-academy-config.sh
EXPOSE 80
```

- [ ] **Step 5: Build the image**

Run:
```bash
cd /c/Users/robla/VScode_Project/HMMstudio/academy
docker build -t hmm-academy:dev .
```
Expected: image built successfully.

- [ ] **Step 6: Run WITHOUT STUDIO_URL and verify config.js is empty-studio**

Run:
```bash
docker run -d --name hmm-academy-test -p 8080:80 hmm-academy:dev
sleep 2
curl -s http://localhost:8080/config.js
```
Expected: contains `studioUrl: ""` and `title: "HMM Academy"`.

- [ ] **Step 7: Verify SPA deep-link + cleanup**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/academy/lesson-2-markov-chains
docker rm -f hmm-academy-test
```
Expected: `200` (nginx fallback serves index.html).

- [ ] **Step 8: Run WITH STUDIO_URL and verify injection**

Run:
```bash
docker run -d --name hmm-academy-test2 -e STUDIO_URL=https://studio.example.com -e ACADEMY_TITLE="My Academy" -p 8081:80 hmm-academy:dev
sleep 2
curl -s http://localhost:8081/config.js
docker rm -f hmm-academy-test2
```
Expected: contains `studioUrl: "https://studio.example.com"` and `title: "My Academy"`.

- [ ] **Step 9: Commit** (pause for approval)

```bash
git add academy/Dockerfile academy/nginx.conf academy/docker-entrypoint.sh academy/.dockerignore
git commit -m "feat(academy): static nginx Docker image with runtime config injection"
```

---

### Task 8: Playwright smoke test

**Files:**
- Create: `academy/e2e/package.json`, `academy/e2e/playwright.config.ts`, `academy/e2e/tests/academy.smoke.spec.ts`

- [ ] **Step 1: Write `academy/e2e/package.json`**

```json
{
  "name": "hmm-academy-e2e",
  "private": true,
  "type": "module",
  "scripts": { "test": "playwright test" },
  "devDependencies": { "@playwright/test": "^1.47.0" }
}
```

- [ ] **Step 2: Write `academy/e2e/playwright.config.ts`** (auto-builds + previews the app)

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: { baseURL: "http://localhost:4173" },
  webServer: {
    // Build then preview the production bundle (serves dist/config.js with the
    // committed default: studioUrl "" => studio button hidden).
    command: "npm --prefix .. run build && npm --prefix .. run preview",
    url: "http://localhost:4173/academy",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 3: Write `academy/e2e/tests/academy.smoke.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test.describe("HMM Academy standalone smoke", () => {
  test("root redirects to /academy and lists lessons", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/academy$/);
    // A few representative lesson titles (heading role to avoid card-desc matches)
    await expect(
      page.getByRole("heading", { name: /What is an HMM\?/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Markov chains/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Viterbi/i }),
    ).toBeVisible();
  });

  test("opens a lesson and renders its body", async ({ page }) => {
    await page.goto("/academy");
    await page.getByRole("link", { name: /Markov chains/i }).click();
    await expect(page).toHaveURL(/\/academy\/lesson-2-markov-chains/);
    await expect(
      page.getByRole("heading", { level: 1, name: /Markov chains/i }),
    ).toBeVisible();
  });

  test("studio button is hidden when no studioUrl configured", async ({
    page,
  }) => {
    // lesson-2 ships a presetTopologyYaml; with studioUrl "" the link must NOT render.
    await page.goto("/academy/lesson-2-markov-chains");
    await expect(
      page.getByRole("link", { name: /Open in HMM Studio/i }),
    ).toHaveCount(0);
  });

  test("mark-complete persists across reload (localStorage store works)", async ({
    page,
  }) => {
    await page.goto("/academy/lesson-1-what-is-an-hmm");
    await page.getByRole("button", { name: /Mark as complete/i }).click();
    await expect(
      page.getByRole("button", { name: /Marked complete/i }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("button", { name: /Marked complete/i }),
    ).toBeVisible();
  });
});
```

- [ ] **Step 4: Install + run the smoke**

Run:
```bash
cd /c/Users/robla/VScode_Project/HMMstudio/academy/e2e
npm install
npx playwright install --with-deps chromium
npm test
```
Expected: 4 passed.

- [ ] **Step 5: Commit** (pause for approval)

```bash
git add academy/e2e/package.json academy/e2e/playwright.config.ts academy/e2e/tests/academy.smoke.spec.ts academy/e2e/package-lock.json
git commit -m "test(academy): Playwright smoke (index, lesson render, hidden bridge, persistence)"
```

---

### Task 9: Template README + sync script

**Files:**
- Create: `academy/README.md`, `academy/scripts/sync-from-studio.sh`

- [ ] **Step 1: Write `academy/scripts/sync-from-studio.sh`** (re-copies the slice; reminds to re-apply the bridge patch)

```sh
#!/bin/sh
# Re-sync the Academy slice from the studio frontend (source of truth).
# Run from the repo root: sh academy/scripts/sync-from-studio.sh
#
# After running, manually re-apply the bridge patch on
# academy/src/pages/LessonPage.tsx (see docs/plans/2026-05-28-academy-standalone.md
# Task 4): drop useNavigate/topologyStore/lib/yaml/handleTryInEditor and use
# <TryInStudioLink yaml={lesson.presetTopologyYaml} /> instead.
set -e
SRC=src/hmm_studio/frontend/src
DST=academy/src
cp "$SRC"/components/academy/*.ts "$SRC"/components/academy/*.tsx "$DST/components/academy/"
cp "$SRC"/lessons/*.ts "$SRC"/lessons/*.tsx "$DST/lessons/"
cp "$SRC/store/academyStore.ts" "$DST/store/academyStore.ts"
cp "$SRC/components/ThemeToggle.tsx" "$DST/components/ThemeToggle.tsx"
cp "$SRC/hooks/useTheme.ts" "$DST/hooks/useTheme.ts"
cp "$SRC/pages/AcademyPage.tsx" "$DST/pages/AcademyPage.tsx"
cp "$SRC/index.css" "$DST/index.css"
echo "Synced. Now re-apply the bridge patch on $DST/pages/LessonPage.tsx (see Task 4)."
```
Note: `LessonPage.tsx` is intentionally NOT auto-copied (it carries the bridge patch). `vite-env.d.ts` is stable and not re-synced.

- [ ] **Step 2: Write `academy/README.md`** (the template contract)

````markdown
# HMM Academy — standalone & template

A self-contained, statically-deployable build of the HMM Studio Academy:
interactive lessons, quizzes, flashcards and D3 visualisations. No backend.

## Quick start (dev)

```bash
npm install
npm run dev        # http://localhost:5173/academy
```

## Build & run with Docker

```bash
docker build -t hmm-academy .
docker run -p 8080:80 hmm-academy                 # pure static learning mode
docker run -p 8080:80 -e STUDIO_URL=https://studio.example.com hmm-academy
```

`STUDIO_URL` and `ACADEMY_TITLE` are injected at **container start** (no rebuild
needed) into `/config.js`. When `STUDIO_URL` is empty, the per-lesson
"Open in HMM Studio" link is hidden.

## Using this as a template for another academy

This app separates a **framework** (don't touch) from **content** (replace):

| Layer | Files | Action |
|---|---|---|
| Content | `src/lessons/` + `src/academy.config.ts` | Replace lessons, edit title |
| Framework | `src/components/`, `src/store/`, `src/Layout.tsx`, `src/App.tsx`, `src/runtimeConfig.ts` | Leave as-is |

Steps: replace `src/lessons/*` with your own lesson components and update
`src/lessons/index.ts` (the manifest), edit `src/academy.config.ts`
(`title`, default `studioUrl`), then `docker build`. The lesson manifest type
(`LessonMeta`) documents every field.

## Staying in sync with the studio Academy

The studio's Academy (`src/hmm_studio/frontend/src/`) is the source of truth for
the HMM lessons. To pull updates into this standalone copy:

```bash
sh scripts/sync-from-studio.sh
# then re-apply the bridge patch on src/pages/LessonPage.tsx (see the plan, Task 4)
npm run lint && npm run build
```
````

- [ ] **Step 3: Commit** (pause for approval)

```bash
git add academy/README.md academy/scripts/sync-from-studio.sh
git commit -m "docs(academy): template README + studio sync script"
```

---

### Task 10: CI workflow

**Files:**
- Create: `.github/workflows/academy.yml`

- [ ] **Step 1: Write `.github/workflows/academy.yml`**

```yaml
name: Academy (standalone)

# Builds the standalone Academy, runs its Playwright smoke, and verifies the
# Docker image + runtime config injection. Scoped to changes under academy/.
on:
  workflow_dispatch:
  push:
    branches: [academy-standalone]
    paths: ["academy/**", ".github/workflows/academy.yml"]
  pull_request:
    paths: ["academy/**", ".github/workflows/academy.yml"]

jobs:
  build-and-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: academy
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install app deps
        run: npm ci
      - name: Typecheck + build
        run: npm run build
      - name: Install e2e deps
        working-directory: academy/e2e
        run: |
          npm ci
          npx playwright install --with-deps chromium
      - name: Run smoke
        working-directory: academy/e2e
        run: npm test
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: academy-playwright-report
          path: academy/e2e/playwright-report/
          retention-days: 7

  docker:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t hmm-academy:ci academy
      - name: Run + verify runtime config injection
        run: |
          docker run -d --name acad -e STUDIO_URL=https://studio.example.com -p 8080:80 hmm-academy:ci
          sleep 3
          curl -sf http://localhost:8080/config.js | grep 'studio.example.com'
          curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/academy/lesson-2-markov-chains | grep 200
          docker rm -f acad
```
Note: `npm ci` in `academy/e2e` requires the e2e lockfile committed in Task 8 — confirm it was added.

- [ ] **Step 2: Commit** (pause for approval)

```bash
git add .github/workflows/academy.yml
git commit -m "ci(academy): build + smoke + docker runtime-config verification"
```

- [ ] **Step 3: Push the branch (pause for explicit user approval — never auto-push)**

```bash
git push -u origin academy-standalone
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Standalone deployable → Tasks 1,5,6,7 (Vite app + nginx Docker). ✓
- Template (framework/content split) → Task 3 (academy.config), Task 9 (README contract). ✓
- 1:1 copy → Task 2 (preserves layout; `/academy` prefix kept so AcademyPage/LessonCard/LessonPage nav unchanged). ✓
- Link-out bridge configurable, hidden when empty → Tasks 3,4 + smoke test 3 (Task 8). ✓
- Static-pure image → Task 7 (nginx, no Python). ✓
- Runtime config injection ("rebuild easy") → Task 7 entrypoint + smoke/CI verification. ✓
- Notebook gallery → copied 1:1 in Task 2 (NotebookLink unchanged; pointing at RoJLD/HMMstudio — configurable base noted as future work, intentionally out of scope to keep sync to a single patch point). ✓
- Anti-divergence → Task 9 sync script. ✓
- Zero Regression verification → Task 6 (typecheck/build), Task 7 (docker curl), Task 8 (Playwright). ✓
- Branch placement → Task 1 (`academy-standalone`). ✓

**Placeholder scan:** No TBD/TODO; every file has full content; the LessonPage patch shows exact old/new. ✓

**Type consistency:** `getStudioUrl()`/`getTitle()` defined in Task 3 are the exact names used in Task 4 (`TryInStudioLink`) and Task 5 (`Layout`). `AcademyConfig`/`DEFAULT_CONFIG` consistent between `academy.config.ts` and `runtimeConfig.ts`. `window.__ACADEMY_CONFIG__` shape matches the entrypoint's generated object (`studioUrl`, `title`). ✓
