# Design — HMM Academy standalone & template

**Date** : 2026-05-28
**Auteur** : Robin Denis (brainstorm avec Claude Code)
**Status** : Draft, en attente de revue utilisateur
**Branche cible** : `academy-standalone`

## Contexte

Le studio `hmm-studio` embarque une **Academy** : 14 leçons web interactives
(React + D3), un moteur de quiz/flashcards, des animations (Baum-Welch, Trellis,
simplexe de probabilité…) et une galerie de notebooks Jupyter (liens Binder /
Colab / GitHub). Cette Academy vit aujourd'hui dans le frontend du studio, à
`src/hmm_studio/frontend/src/`.

Audit du graphe de dépendances : l'Academy est une **bounded context quasi-pure**.
Le seul couplage hors de son périmètre se trouve dans
`pages/LessonPage.tsx`, pour le bridge « Try in editor » :

```ts
const partial = yamlToTopology(lesson.presetTopologyYaml);
useTopologyStore.getState().loadTopology(partial);
navigate("/topology");
```

→ deux imports seulement (`store/topologyStore`, `lib/yaml`), exclusivement pour
ce bouton. Tout le reste (composants, leçons, store académique) ne dépend que de
`react`, `react-router-dom`, `d3`, `zustand` et Tailwind. **Pas** de `reactflow`
ni `zundo` (réservés au topology editor).

## Objectif

Sur une branche dédiée `academy-standalone`, produire un dossier `academy/`
auto-contenu qui est **à la fois** :

1. **Une app standalone déployable** : l'Academy seule, buildée en assets
   statiques, servie par nginx dans une image Docker légère, rebuildable
   trivialement.
2. **Un template réutilisable** : une « coquille » framework (renderer de leçons,
   moteur de quiz, store, layout, composants D3) séparée d'une « couche contenu »
   (les leçons + un fichier de branding) que l'on remplace pour fabriquer une
   *autre* academy (autre sujet, autre marque) sans toucher au framework.

Le tout en **copiant 1:1** le slice Academy existant (zéro réécriture du contenu
pédagogique), avec une stratégie de re-synchronisation documentée pour éviter la
divergence.

## Non-objectifs

- Pas de backend Python dans l'image standalone (statique-pure).
- Pas de refactor du frontend studio existant (l'Academy y reste intacte ;
  l'app standalone en est un **miroir reproductible**, pas un déplacement).
- Pas de monorepo / workspace partagé (rejeté, voir Alternatives).
- Pas de réimplémentation du topology editor dans le standalone.

## Décisions de design

| Sujet | Décision | Justification |
|---|---|---|
| **Bridge « Try in editor »** | Link-out configurable via `STUDIO_URL` ; bouton masqué si non défini | Image statique-pure ; supprime le seul couplage backend ; point d'extension propre |
| **Périmètre** | Leçons web + quiz/flashcards + cartes notebook (liens externes) | Tout le frontend ; notebooks liés (base URL configurable), non embarqués |
| **Backend Docker** | nginx statique + injection de config au runtime | « Rebuild facile » : changer l'URL studio ne nécessite **aucun** rebuild, juste `docker run -e` |
| **Placement** | Branche `academy-standalone`, nouveau dossier racine `academy/` | Demande utilisateur : « branche dédiée » + « copiant 1:1 » |
| **Approche** | A — app Vite sœur (copie 1:1) | Risque minimal, livrable le plus propre (voir Alternatives) |

## Architecture (Approche A)

### Arborescence `academy/`

```
academy/
├── Dockerfile              # multi-stage: node:20 build → nginx:alpine
├── docker-entrypoint.sh    # env vars → /config.js au démarrage du conteneur
├── nginx.conf              # SPA fallback: try_files $uri /index.html
├── .dockerignore
├── package.json            # deps minimales (pas de reactflow/zundo)
├── vite.config.ts          # define __APP_VERSION__
├── tailwind.config.js      # couleurs brand (copiées)
├── postcss.config.js
├── tsconfig.json / tsconfig.node.json
├── index.html
├── README.md               # CONTRAT TEMPLATE : comment forker pour une autre academy
├── academy.config.ts       # branding par défaut (titre, sous-titre, footer, flags)
├── public/config.js        # placeholder, remplacé au runtime par l'entrypoint
├── scripts/
│   └── sync-from-studio.sh # re-copie le slice depuis le frontend studio + patch bridge
├── e2e/                     # smoke Playwright (optionnel mais recommandé)
└── src/
    ├── main.tsx            # racine React + BrowserRouter
    ├── App.tsx             # routes: "/" (index) + "/:lessonId"
    ├── index.css           # directives Tailwind (copiées)
    ├── runtimeConfig.ts    # lit window.__ACADEMY_CONFIG__ ?? import.meta.env ?? academy.config
    ├── Layout.tsx          # shell Academy-only (titre config + ThemeToggle + version)
    ├── components/
    │   ├── ThemeToggle.tsx          # copié 1:1
    │   ├── TryInStudioLink.tsx      # remplace le bridge (link-out)
    │   └── academy/                 # 17 composants copiés 1:1
    ├── pages/
    │   ├── AcademyIndex.tsx         # = AcademyPage 1:1 (chemins d'import ajustés)
    │   └── LessonPage.tsx           # 1:1 sauf bridge → <TryInStudioLink>
    ├── lessons/                     # 14 leçons + index.ts copiés 1:1  ← COUCHE CONTENU
    └── store/
        └── academyStore.ts          # copié 1:1
```

### Couche framework vs couche contenu (template)

- **Framework** (stable — on n'y touche pas en forkant) : `main`, `App`, `Layout`,
  `runtimeConfig`, `components/` (renderer, quiz engine, D3, flashcards),
  `store/academyStore`.
- **Contenu** (remplacé pour une autre academy) : `src/lessons/` +
  `academy.config.ts`. **Forker = remplacer ces deux-là, puis rebuild.** Le
  `README.md` documente ce contrat explicitement.

### Le bridge → `<TryInStudioLink>`

Composant qui lit `runtimeConfig.studioUrl` :

- si défini → rend `<a target="_blank" rel="noopener" href={studioUrl + "/topology"}>↗ Open in HMM Studio</a>`
  (le preset YAML pourra être passé en query string `?preset=<base64>` plus tard,
  côté studio — évolution future, non bloquante) ;
- si vide/undefined → ne rend rien.

Supprime les imports `topologyStore` et `lib/yaml` de `LessonPage`. Le champ
`presetTopologyYaml` du manifest reste (inoffensif) ; il pilote juste la présence
du lien.

### Config runtime (cœur du « rebuild facile »)

L'image est buildée **une seule fois**. Au démarrage du conteneur,
`docker-entrypoint.sh` génère `/usr/share/nginx/html/config.js` :

```js
window.__ACADEMY_CONFIG__ = {
  studioUrl: "${STUDIO_URL}",
  notebookBaseUrl: "${NOTEBOOK_BASE_URL}",
  title: "${ACADEMY_TITLE}",
};
```

`index.html` charge `<script src="/config.js"></script>` avant le bundle.
`runtimeConfig.ts` lit `window.__ACADEMY_CONFIG__`, avec fallback sur
`import.meta.env.VITE_*` (mode `npm run dev`) puis sur les valeurs par défaut de
`academy.config.ts`. Conséquence :

```sh
docker run -e STUDIO_URL=https://studio.example.com -p 8080:80 hmm-academy
```

change l'URL studio **sans rebuild**. Un rebuild n'est nécessaire que pour
changer le **contenu** des leçons — et reste un simple `docker build academy/`.

### Galerie notebooks

Les cartes `NotebookLink` sont conservées. Leurs liens (Binder / Colab / GitHub /
Download) sont construits à partir de `runtimeConfig.notebookBaseUrl` (défaut :
le repo GitHub HMMstudio). Les fichiers `.ipynb` ne sont **pas** embarqués dans
l'image par défaut.

## Stratégie anti-divergence

Source de vérité = l'Academy du studio. `academy/scripts/sync-from-studio.sh` :

1. copie `src/hmm_studio/frontend/src/{components/academy,lessons,store/academyStore.ts,components/ThemeToggle.tsx,pages/AcademyPage.tsx,pages/LessonPage.tsx}` vers `academy/src/…` ;
2. réapplique le patch du bridge sur `LessonPage.tsx` (remplacement par `<TryInStudioLink>`).

Documenté dans le README ; non-automatique (lancé manuellement après évolution de
l'Academy studio).

## Vérification (Zero Regression)

- **Smoke Playwright** (`academy/e2e/`) : l'index liste les 14 leçons ; ouvrir une
  leçon rend son contenu ; un quiz se complète ; le bouton studio est **masqué**
  quand `STUDIO_URL` est vide et **présent** quand il est défini.
- **Build typecheck** : `tsc && vite build` doit passer.
- **CI** : `.github/workflows/academy.yml` (déclenché sur push de la branche /
  PR touchant `academy/`) build l'image Docker et lance le smoke.

## Alternatives écartées

- **B — extraction au build** (2e config Vite dans le frontend studio) : source
  unique, mais pas un template propre (entremêlé au studio), Docker build depuis
  le frontend studio, `reactflow`/`zundo` restent dans `node_modules`. Ne
  satisfait pas l'exigence « template ».
- **C — package workspace partagé** (`packages/academy-core`) : source unique +
  standalone + template, mais gros refactor monorepo, touche le build studio,
  risque élevé, surdimensionné pour le besoin actuel.

## Risques

- **Divergence** studio ↔ standalone → mitigée par le script de sync + CI.
- **`__APP_VERSION__`** : doit être défini dans `vite.config.ts` du standalone
  (le studio l'injecte ailleurs).
- **Dark mode** : les leçons utilisent des classes `dark:` ; `ThemeToggle` +
  `darkMode: "class"` Tailwind doivent être copiés pour préserver le rendu.
- **Chemins d'import** : la copie 1:1 conserve les imports relatifs internes au
  slice ; seuls `AcademyPage`/`LessonPage` changent de chemin (déplacés sous
  `academy/src/pages/`).

## Plan de livraison (esquisse, détaillé par writing-plans)

1. Scaffold `academy/` (Vite app minimale, configs, Docker, nginx, entrypoint).
2. Copier le slice 1:1 + ajuster les chemins des deux pages.
3. Patch bridge → `<TryInStudioLink>` + `runtimeConfig`.
4. `academy.config.ts` + README (contrat template).
5. Script `sync-from-studio.sh`.
6. Smoke Playwright + workflow CI.
7. Build local + run Docker de vérification.
