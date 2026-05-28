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
