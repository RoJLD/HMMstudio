---
Status: current
---

# Refonte UX de l'éditeur de topologie (states espacés, drag réparé, flèches de probabilité, et passe UX P0/P1/P2)

*Spec écrite le 2026-06-02. Déclenchée par un retour utilisateur (Robin) :
« quand j'ajoute un HMM mes états sont collés, il faudrait optimiser le visuel
d'emblée et pouvoir déplacer les bulles ; j'aimerais des flèches avec les
probabilités de transition ». Précédée d'un audit multi-agents de l'éditeur
React Flow (7 agents, voir le journal de session). Périmètre validé avec
l'utilisateur : pack complet **P0 + P1 + P2**.*

## 1. Contexte / problème

L'éditeur de topologie (`src/hmm_studio/frontend/src/components/topology/`,
React Flow v11.11.4, store zustand `topologyStore.ts` avec undo `zundo` +
persist localStorage) souffre de trois familles de défauts, tous confirmés par
lecture du code.

### 1.1 Les états apparaissent « collés »

Trois causes se cumulent :

1. **Pas de grille trop petit à la création.** Toute topologie chargée (wizard,
   import YAML, URL partagée, leçon) passe par `yamlToTopology()` qui assigne une
   grille en dur : `x = 80 + (i % 4) * 180`, `y = 80 + ⌊i/4⌋ * 140`
   ([yaml.ts:121-125]). Un nœud `StateNode` est une pilule *content-sized* :
   `px-4 py-2 rounded-full border-2 min-w-[80px]` ([StateNode.tsx:13-20]) ⇒
   **~116 px minimum**, davantage avec le label. 180 − 116 ≈ **64 px** de trou
   brut seulement, et ce trou grandit avec la longueur du label.
2. **`fitView` sur-zoome les petits graphes.** `<ReactFlow fitView>`
   ([EditorCanvas.tsx:111]) agrandit un graphe à 3 nœuds pour remplir le canvas,
   réduisant les 64 px à ~0 à l'écran.
3. **Ajout manuel aléatoire.** Le bouton « + state » place le nœud à un point
   `Math.random()` ([Toolbar.tsx:22-29]) sans anti-collision ⇒ deux ajouts
   peuvent se superposer.

Aucun moteur d'auto-layout n'existe (pas de dagre/elk ; `package.json` ne dépend
que de `reactflow`).

### 1.2 Le drag « ne marche pas » (en réalité : pas de feedback visuel)

ReactFlow tourne en **mode contrôlé** (props `nodes` + `onNodesChange`). Dans
`onNodesChange` ([EditorCanvas.tsx:70-71]), `applyNodeChanges(changes, nodes)`
est appelé mais **sa valeur de retour est jetée** (fonction pure, rien n'est
réassigné). Il n'existe aucun état local de nœuds. Le tableau `nodes` est
re-dérivé à chaque render depuis `store.states[].position`, qui ne change qu'au
**drag-end** (`moveState` sur `dragging === false`, [EditorCanvas.tsx:56-65]).

Conséquence : pendant le glissement la bulle **reste figée** puis saute à la
position de relâchement. La position finale **est** bien commitée et persistée
(localStorage `hmm-studio-topology`, survit au reload). Donc ce n'est pas un
problème de persistance ni de `nodesDraggable` (true par défaut, non
surchargé) : **c'est l'absence de feedback en cours de drag**. Le commentaire
« Apply locally too so the canvas reflects in-flight drags » décrit une
intention que le code ne réalise pas.

### 1.3 Pas de flèches avec probabilités — et une nuance à préserver

Une arête de l'éditeur **ne porte pas** de probabilité. Son type est
`TransitionEdge { id, source, target, prior_weight? }` ([topologyStore.ts:42-47]).
Elle encode l'appartenance au **masque** des transitions autorisées (sérialisé
en `allowed_transitions`, [yaml.ts:55-108]) plus un poids de Dirichlet optionnel
(`α`). Aujourd'hui l'éditeur n'affiche un label `α=<n>` que si un override est
posé, et l'épaisseur du trait est constante.

Aujourd'hui l'éditeur n'affiche un label `α=<n>` que si un override est posé, et
l'épaisseur du trait est **binaire** (2 vs 3 selon présence d'override), **pas
proportionnelle à une probabilité**.

Les **vraies probabilités de transition** n'existent **qu'après un fit**
(`fitted.model.transmat_`, servi par `GET /api/fit/{job_id}/transmat`,
[app.py:262-289]) et sont **déjà affichées** côté Results par `TransmatGraph`
(épaisseur ∝ proba, bulle `0.42`, flèche `MarkerType.ArrowClosed`). Le rendu
y est fait via des **arêtes React Flow par défaut** stylées par props (≈15
lignes, [TransmatGraph.tsx:122-137]), donc réutilisable presque tel quel.

> **Nuance de conception non négociable :** ce qu'on affiche dans l'éditeur
> (pré-fit) n'est PAS une probabilité apprise. Tout nombre montré sur une arête
> de l'éditeur doit être étiqueté « prior / aperçu », jamais « apprise ».

### 1.4 Lacunes UX plus larges (relevées à l'audit)

Self-loops invisibles et quasi-incréables alors qu'ils sont *le* concept central
d'un HMM (diagonale du transmat) ; pas d'auto-layout ni de minimap ni de
snap-to-grid ; arêtes bidirectionnelles i↔j qui se superposent ; validation
backend réduite à une chaîne de texte dans le panneau (pas de repère spatial) ;
canvas vide sans onboarding ; quasi pas de raccourcis clavier ; nœuds
indifférenciés visuellement ; accessibilité faible (souris-only, statut par
couleur seule) — gênant pour le wedge enseignement.

## 2. Objectif

Rendre l'éditeur de topologie **lisible d'emblée, manipulable et pédagogique**,
sans changer le périmètre de modélisation (toujours : éditer un masque de
transitions + des priors, le fit reste backend). En une phrase : *ouvrir
l'éditeur doit donner un graphe propre et espacé, des bulles qui suivent le
curseur, des flèches qui parlent (masque + aperçu de prior honnête), et les
affordances attendues d'un éditeur de graphe moderne — y compris les self-loops,
un bouton « ranger », et une base d'accessibilité.*

Le travail est découpé en **5 lots** (A→E), livrables et testables
indépendamment, du correctif pur (sans nouvelle dépendance) vers le confort.

## 3. Design

> **Note de revue (2026-06-02)** : ce spec a été durci par un panel adversarial
> (3 relecteurs lisant le spec + le code). Il a confirmé les diagnostics et les
> numéros de ligne, et levé 2 blockers (sélection sur le même canal contrôlé que
> le drag ; positions non sérialisées) + plusieurs majeurs, tous intégrés
> ci-dessous (§3.0 prérequis, A1, B1/B2, C1, D1/D3, §6).

### 3.0 Prérequis transverses (partagés par plusieurs lots)

Trois mécanismes manquent au code actuel et conditionnent plusieurs lots — à
poser **en premier** :

- **P-1 — Registre `edgeTypes` + sélection de type par arête.** Aujourd'hui
  `edges.map` code en dur `type: "default"` ([EditorCanvas.tsx:39]) et il n'y a
  pas de prop `edgeTypes` sur `<ReactFlow>`. Les self-loops (C1), les arêtes
  bidirectionnelles courbées (B3) et tout rendu enrichi en dépendent. Définir un
  `edgeTypes = { selfLoop, curved }`, le passer à `<ReactFlow>`, et brancher la
  dérivation : `t.source===t.target ? 'selfLoop' : pairInverseExiste ? 'curved' : 'default'`.
  Conséquence cachée : un self-loop peut **déjà** exister dans le modèle (le `+
  state`/connect le permet via `addTransition(id,id)`) mais est aujourd'hui
  **invisible** → P-1 est aussi un correctif de bug latent.
- **P-2 — Sérialisation des positions (décision, lève le blocker 2).**
  `yamlToTopology()` régénère **toujours** la grille et ne relit jamais les
  positions ([yaml.ts:121-125]) ; `topologyToYAML()` n'émet **jamais** de
  positions. Donc un layout (Tidy D1 ou drag manuel) **ne survit ni à
  export/import ni au partage d'URL**. **Décision retenue** : (a) garder la
  topology YAML **pure** (pas de positions dans le contrat de modèle, le backend
  n'en a pas besoin), et **remplacer la grille bête** de `yamlToTopology` par un
  **auto-layout par défaut** (P-3, selon la forme détectée) ⇒ tout chargement est
  propre ; (b) ajouter un bloc **optionnel** `_layout` (positions par nom d'état)
  au **payload de partage d'URL et au snapshot localStorage uniquement**, relu
  s'il est présent, ignoré sinon (back-compat). Ainsi un layout délibérément
  rangé survit au reload et au partage, sans polluer le YAML de modèle. ⇒ le lot
  B garde bien « `yaml.ts` (sérialisation modèle) inchangé », mais P-2 touche le
  chemin de **partage/persistance** (séparé).
- **P-3 — Action store `setPositions(Map<id,pos>)` atomique.** Le store
  `temporal()` n'a aucun throttle ([topologyStore.ts:120-214]) ⇒ `moveState`
  pousse une entrée d'undo **par nœud**. Un Tidy sur K nœuds = K entrées (et
  dépasse la limite 50 pour un grand graphe). Ajouter `setPositions` qui écrit
  toutes les positions en **un seul `set()`** ⇒ Tidy = **un seul Ctrl+Z**. À
  utiliser par D1 (Tidy) et tout auto-layout.

### 3.1 Lot A — Correctifs de base (bugfix, zéro feature, zéro dépendance)

| # | Correctif | Fichier | Approche |
|---|---|---|---|
| A1 | **Drag qui suit le curseur** | EditorCanvas.tsx:71 | État local `rfNodes` (voir détail A1 ci-dessous) ; `onNodesChange` fait passer **tous** les types de changements dans `setRfNodes(nds => applyNodeChanges(changes, nds))` ; **garder** le commit `moveState` sur `dragging === false`. Passer `nodes={rfNodes}`. |
| A2 | **Espacement à la création** | yaml.ts:124 | Cf. P-2/P-3 : la grille bête est remplacée par l'auto-layout par défaut (D1) ; à défaut transitoire, pas 180→**240** (x), 140→**160** (y). |
| A3 | **fitView borné** | EditorCanvas.tsx:111 | `fitViewOptions={{ padding: 0.3, maxZoom: 1 }}` ⇒ ne pas sur-zoomer un petit graphe. |
| A4 | **Anti-superposition à l'ajout** | Toolbar.tsx:24 | Placer le nouveau nœud **au centre du viewport** + nudge anti-collision (scanner les positions existantes, décaler tant qu'il y a chevauchement). Nommer par **plus petit index `s` libre** (pas `s${states.length}`, qui duplique après suppression). |
| A5 | **Largeur de bulle bornée** | StateNode.tsx:13-20 | `max-w-[160px]` + `truncate` sur l'`<input>` du label ⇒ la pilule ne dépasse jamais le pas de grille. |

**Détail A1 (load-bearing — corrige le blocker sélection).** ReactFlow contrôlé
porte **aussi** la sélection sur le canal `onNodesChange` : un changement de type
`select` doit revenir dans le tableau contrôlé, sinon l'anneau de sélection et le
panneau latéral (qui lit `selectedStateId`) sautent à chaque commit (rename,
addTransition, drop, edit de prior). Donc :
- `onNodesChange` applique **tous** les types (`position`, `select`, `remove`,
  `dimensions`) via l'updater fonctionnel `setRfNodes(nds => applyNodeChanges(changes, nds))`
  (jamais la closure `nodes` périmée). Le `remove` doit aussi appeler
  `removeState` **et** retirer le nœud de `rfNodes`.
- L'effet de réconciliation (déclenché quand l'identité de `states` change :
  commit, add, remove, **load YAML**) **fusionne par id** : il met à jour
  `position`/`data` depuis le store mais **préserve** les champs transitoires que
  React Flow maintient en place (`selected`, `dragging`, `positionAbsolute`,
  `width`/`height` mesurés). **Ne pas** reconstruire les nœuds à plat depuis
  `states.map(...)` (ça efface sélection + dimensions mesurées).

**Pourquoi cette approche (vs alternatives) :** on garde la source de vérité dans
le store mais on ajoute un canal *in-flight* local plutôt que d'écrire à chaque
frame — écrire par frame inonderait zundo et localStorage (rejeté). Le commit
reste **une fois** par drag.

**Piège connu (corrigé) :** il n'y a **pas** de boucle infinie (l'effet n'écrit
pas dans le store ; l'identité de `states` est stable entre mutations). Le vrai
risque est la **perte des champs transitoires** au re-seed (sélection effacée,
dimensions re-mesurées) → d'où la fusion-par-id ci-dessus. Tester : l'anneau de
sélection et le panneau latéral **persistent** à travers un rename et un
drag-drop ; les positions survivent au reload.

### 3.2 Lot B — Flèches & probabilités (feature, honnêteté préservée)

- **B1 — Helper partagé `probEdgeStyle(p)`.** Extraire la recette de
  [TransmatGraph.tsx:122-137] (`strokeWidth = 1 + 5p`, `stroke =
  rgba(79,70,229, 0.3+0.7p)`, `label = p.toFixed(2)`, pilule `labelBg*`,
  `MarkerType.ArrowClosed`) dans un module partagé importé par **TransmatGraph
  ET EditorCanvas**, pour éviter la divergence. Aucune nouvelle dépendance.
  **Portée du helper** : il ne renvoie **que** le mapping pur `p → style`
  (stroke/strokeWidth/label/labelBg/markerEnd). La branche `isActive`/`animated`
  (épaisseur 4, indigo, animation liée au player Viterbi) **reste locale à
  TransmatGraph** (pas d'analogue dans l'éditeur). Conséquence assumée :
  unifier la **couleur de flèche** (l'éditeur utilise `#94a3b8`/`#4f46e5`,
  TransmatGraph `#6366f1`) est un **petit changement visuel volontaire** de
  l'éditeur, pas un no-op. (Idem pour la math de cercle de D1.2 : à extraire dans
  le même lib partagé, pas à recopier — cf. P-1/B1, même risque de divergence.)
- **B2 — Aperçu de la moyenne du prior (toggle, OFF par défaut).** Pour chaque
  arête : `p = α_eff(edge) / Σ α_eff(out-edges du source)`, avec
  `α_eff = e.prior_weight ?? globalAlpha ?? 1`. C'est la **moyenne du prior de
  Dirichlet = la probabilité de transition *attendue avant tout fit*** (et **pas**
  la force du lissage, cf. ci-dessous). Calculé côté éditeur à partir des arêtes
  groupées par `source` (pas besoin de mapping index↔id). Détails :
  - **Sans aucun override**, ça dégénère proprement en **uniforme `1/degré-sortant`**.
  - En mode MLE (`globalAlpha === null`) : afficher **toujours** `1/degré`
    étiqueté « uniforme », en **ignorant** d'éventuels overrides isolés (sinon
    `?? 1` produirait un nombre pondéré qu'on appellerait à tort « uniforme »).
    *(Décider à l'implémentation : MLE = toujours uniforme ; les overrides ne
    s'affichent en pondéré que si un `globalAlpha` numérique existe.)*
  - **Garde-dénominateur** : degré sortant 0 (état puits, cf. C2) ⇒ **pas de
    label** (ou « — ») ; un self-loop **compte** comme arête sortante de sa
    source.
  - **Honnêteté (renforcée par la revue) :** le nombre est **invariant à
    l'échelle de α** — pour `globalAlpha ∈ {1, 2, 100}` sans override il affiche
    la même valeur, alors que l'**effet** sur le fit diffère radicalement
    (`pseudo = max(α−1, 0)`, cf. `fit/_base.py`). Donc le libellé est
    **« moyenne du prior (P attendue avant fit) »** et **ne doit jamais** être
    vendu comme « voir ce que fait augmenter α ». Test de verrouillage : aperçu
    **identique** pour α ∈ {1, 2, 100} sans override.
  - **Propriété du toggle** : préférence **UI seule**, hors `topologyStore`
    (clé localStorage dédiée ou état composant). **Interdit** de l'ajouter à
    `TopologyData`/`temporal`/`partialize` (sinon toggler l'aperçu deviendrait
    une action *undoable* polluant l'historique). Idem pour les toggles
    snap-to-grid (D2) et guides (D4) s'ils deviennent activables.
  - Valeur **d'affichage dérivée uniquement** : rien écrit au store,
    **sérialisation modèle `yaml.ts` inchangée** ; label `α=` des overrides
    conservé et distinct.
- **B3 — Arêtes courbées bidirectionnelles.** Via le type `curved` du registre
  P-1 : quand `(a,b)` ET `(b,a)` existent, rendre deux arêtes bombées en sens
  opposés (smoothstep/bezier à courbure, ou offset de handle par direction) et
  placer les labels à ~30 %/70 % du chemin, pour que les deux probas asymétriques
  `P(i→j) ≠ P(j→i)` restent lisibles.

**Pourquoi (vs alternatives) :** afficher l'aperçu **par défaut** risquerait de
laisser croire à une proba apprise → toggle OFF. On réutilise **que** le style
d'arête de TransmatGraph, pas son layout circulaire : l'éditeur garde ses nœuds
déplaçables. Montrer l'`α` brut sur **toutes** les arêtes (option écartée)
embrouille le sens masque/prior ; le toggle « moyenne du prior » est plus clair
**et** honnête sur ce qu'il représente.

### 3.3 Lot C — Structure HMM (P0/P1)

- **C1 — Self-loops visibles et créables (P0).** Via le type `selfLoop` du
  registre P-1 : détecter `t.source === t.target` dans `edges.map` et rendre un
  **arc SVG** repassant au-dessus de la pilule. Affordance de création : un bouton
  « ↺ » sur le nœud sélectionné appelant `addTransition(id, id)` (le garde
  autorise déjà `source === target`, [topologyStore.ts:149-160]). Style proba/α
  identique aux autres arêtes. *Alternative écartée : un simple badge sur le nœud
  — moins fidèle au sens « transition vers soi ».* (Rappel : sans P-1 ces arêtes
  existent déjà dans le modèle mais sont invisibles — c'est aussi un bugfix.)
- **C2 — Linter structurel client (P1).** Fonction pure sur `states+transitions`
  flaggant : état **inatteignable**, état **puits** (aucune sortante ni self-loop
  ⇒ ligne du transmat non normalisable), nœuds isolés. **Définition du « set de
  départ »** (sinon le test est vacant) — dépend de `startprob`
  ([topologyStore.ts:54]) : `'uniform'` ⇒ **tous** les états sont départ (donc
  « inatteignable » dégénère ; reporter plutôt **« aucune arête entrante »** comme
  warning) ; `'first_state'` ⇒ `{state[0]}` ; `number[]` ⇒ états à `prob > 0`. BFS
  d'atteignabilité depuis ce set. Rendu : anneau/badge ambre (warning) ou rouge
  (erreur) sur le `StateNode` + tooltip + compteur Toolbar. La validation backend
  (émission/params) reste l'autorité ; ceci ajoute le **repère spatial**.

### 3.4 Lot D — Layout & navigation (P0/P1)

- **D1 — Bouton « Tidy » / auto-layout (P0).** Split-button Toolbar, 3 modes
  HMM-aware réécrivant **toutes** les positions via **`setPositions` (P-3, un
  seul `set()` ⇒ un seul undo)** — surtout **pas** `moveState` par nœud (qui ferait
  K entrées d'undo et déborderait la limite 50). Modes : (1) **Left-right / chaîne**
  (tri par index, une rangée, pas > largeur max, self-loops au-dessus) ;
  (2) **Cercle / ergodique** (math `cx + R·cos(a)`, `R = max(110, 26K)` —
  **extraire** depuis [TransmatGraph.tsx:81-109] vers le lib partagé, pas
  recopier) ; (3) **Layered** (passe hiérarchique gauche→droite). Auto-détection
  chaîne-like vs ergodique pour le défaut. **Décision dépendance** : modes 1 et 2
  en **zéro-dépendance** d'abord ; le mode 3 (layered) **n'est inclus que s'il
  reste zéro-dep faisable** — sinon **différé** (cf. Questions ouvertes). C'est
  aussi l'auto-layout par défaut appelé au chargement (P-2/A2) et le remède
  durable aux états collés. *Done : Tidy range proprement left-right et
  ergodique, et **un seul Ctrl+Z** restaure la disposition d'avant.*
- **D2 — Minimap + snap-to-grid (P1).** Ajouter `<MiniMap/>` (couleur par type
  d'émission, cf. E2), garder `<Controls/>`, et `snapToGrid` + `snapGrid={[16,16]}`
  sur `<ReactFlow>`. Built-ins reactflow, risque quasi nul.
- **D3 — Onboarding canvas vide (P1).** Overlay `EmptyCanvas` quand
  `states.length === 0` : carte « Start here » + 3 presets cliquables (3-state
  Left-right / 3-state Ergodic / 4-state Bakis). **Réutiliser** la machinerie du
  wizard — `buildTopologyYaml({ shape, k, stateNames: defaultNames(k), … })` qui
  appelle `allowedTransitionsForShape` ([buildTopologyYaml.ts:54-64]) et la liste
  `SHAPES` ([WizardPage.tsx]) — **pas** une seconde copie du mapping forme→arêtes
  (qui dériverait : p. ex. `ergodic` = `allowed_transitions` vide = pleinement
  connecté par convention backend). Puis `loadTopology`. + liens « wizard guidé »
  et « importer YAML ». *Done : le set de transitions de chaque preset ==
  `allowedTransitionsForShape(shape, names)`.*
- **D4 — Guides d'alignement au drag (P2).** Pendant le drag, détecter les nœuds
  partageant ~le même x/y, tracer une ligne-guide et snapper avant commit.

### 3.5 Lot E — Confort & inclusion (P2)

- **E1 — Raccourcis clavier.** `a`/`n` = ajouter un état (au centre du viewport,
  pas aléatoire) ; `Ctrl/Cmd+Z` / `+Shift+Z` = undo/redo (zundo déjà câblé) ;
  `l` = Tidy ; `r` = renommer le nœud sélectionné ; Delete déjà géré. **Garde-fou
  de focus** : se baser sur `document.activeElement` (tagName `INPUT`/`TEXTAREA`
  ou `isContentEditable`) — attention, `StateNode` rend le label comme un
  `<input>` toujours présent ([StateNode.tsx:26-31]) ⇒ exclure ce champ-label du
  swallow quand le nœud est sélectionné mais le label pas en édition. Popover
  « ? » de légende. *(Le chemin `remove` du Delete doit, via A1, élaguer
  `rfNodes` + appeler `removeState`.)*
- **E2 — Couleur des nœuds par caractère d'émission.** Teinte/badge par
  `emission.type` (gaussian/gmm/multinomial/poisson) + distinction des états
  porteurs d'`init hints` ; légende ; même couleur dans la minimap. Subtil
  (anneau d'accent), pas arc-en-ciel.
- **E3 — Grille de masque K×K cliquable — ⏸ DÉFÉRÉE hors de ce chantier.**
  Side-tab miroir du heatmap Results (cellules autorisées remplies / interdites
  barrées, clic = toggle d'arête). Correctement scopée (renforce « arête = masque,
  pas proba ») mais c'est une **seconde surface d'édition** à tenir synchrone avec
  le même store, pour un bénéfice marginal vs la plainte utilisateur. **Sortie de
  ce chantier**, parquée en ticket/spec de suivi. Si un jour reprise : le canvas
  reste **source de vérité unique** (la grille n'est qu'une vue appelant
  `addTransition`/`removeTransition`, aucun état propre).
- **E4 — Accessibilité.** `aria-label` par nœud (« State s0, gaussian, 2
  transitions sortantes, sélectionné »), `role`/`tabIndex` focusables +
  navigation flèches, focus rings `:focus-visible`, statut **couleur + icône/texte**
  (⚠/« error »/« ok », pas couleur seule), chemin clavier pour connecter
  (sélection source → `c` → cible).

## 4. Bornes de scope (hors-périmètre)

- **Pas de nouveau modèle ni de nouvelle sémantique.** L'éditeur reste un éditeur
  de **masque + priors** ; les probabilités apprises restent côté fit/Results.
  (Cohérent avec [[hmm-studio-scope-discipline]] : c'est du polish UI, pas une
  extension HMM-land.)
- **Pas d'affichage de probabilités fittées dans l'éditeur** (elles sont
  keyées par `job_id`, pas par la topologie live). L'éditeur montre au plus un
  **aperçu de prior** étiqueté.
- **Store : pas de refonte**, mais **un ajout ciblé** : l'action atomique
  `setPositions` (P-3) pour rendre Tidy *undoable* en un coup. La persistance
  existante reste ; on ajoute un bloc **optionnel** `_layout` au **payload de
  partage et au snapshot localStorage** (P-2), pas au YAML de modèle.
- **Pas de collaboration temps-réel / multi-utilisateur / serveur de layout.**
- **`yaml.ts` (sérialisation *du modèle*) reste inchangé** — ni l'aperçu B2 ni
  les positions n'entrent dans le YAML de topologie (purété modèle). Les positions
  durables passent par le chemin `_layout` séparé (P-2).
- **E3 (mask grid)** : hors de ce chantier (ticket de suivi).
- Le **mode layered (D1.3)** et toute **dépendance dagre/elk** sont
  conditionnels (cf. Questions ouvertes) — différés si non zéro-dep.

## 5. Questions ouvertes

1. **Dépendance d'auto-layout (D1.3).** Recommandation : livrer left-right +
   circular en zéro-dep ; **différer** le mode layered (et donc dagre/elk) à un
   lot ultérieur si le besoin se confirme. *À confirmer au plan.*
2. **Aperçu de prior par défaut (B2).** Recommandation : **toggle OFF par
   défaut**, libellé « aperçu de prior — non fitté ». *À confirmer.*
3. **Durabilité des positions (résolu par P-2).** Décision : YAML modèle pur +
   auto-layout par défaut au chargement (remplace la grille bête) + bloc
   `_layout` optionnel sur le chemin partage/localStorage uniquement. ⇒ un layout
   rangé survit au reload et au partage ; l'import d'un YAML « nu » donne un
   auto-layout propre (pas la grille collée). *Reste à confirmer : relit-on
   `_layout` aussi à l'import de fichier YAML, ou seulement au partage d'URL ?*
4. **Rendu self-loop (C1).** Recommandation : arête custom (arc) plutôt que badge.
   *(retenu)*
5. **E3 (mask grid).** **Sortie** de ce chantier (ticket de suivi) — cf. §3.5/§4.
6. **Runner de tests JS (nouveau, soulevé en revue).** Il n'existe **aucun**
   runner unitaire JS/TS (frontend : `dev/build/preview/lint` seulement ; seul
   Playwright e2e existe, package séparé). Recommandation : **ajouter vitest** au
   frontend (Vite-natif, c'est le bon tier pour `probEdgeStyle`, le calcul
   d'aperçu, le linter, l'auto-layout — fonctions pures) et le câbler dans
   `ci.yml`. Justifié par la discipline « ne pas créer d'infra parallèle » :
   il n'y a pas de tier unitaire existant à réutiliser, et Playwright ne convient
   pas pour tester un helper de style/proba. *À acter au plan.*

## 6. Séquencement et critères de « done »

Ordre (revu pour **front-loader les 3 demandes verbatim de l'utilisateur** —
collés, drag, flèches-proba — avant le structurel qu'il n'a pas demandé) :

0. **Prérequis P-1/P-2/P-3** (~½ j) — registre `edgeTypes`, décision positions
   (`_layout` + auto-layout au load), action `setPositions`. Débloque A/B/C/D.
1. **Lot A** (bugfix, **~1 j** — revu à la hausse : la réconciliation contrôlée
   drag/sélection + bornage de largeur est un classique chronophage). *Done :*
   drag suit le curseur **sans** snap-back, **sélection + panneau persistent** à
   travers rename et drop, positions survivent au reload, k=2/3/5 et wrap >4
   espacés, ajout sans superposition ni collision de nom après suppression.
2. **Lot B** (flèches/proba, ~1 j) — **remonté en 2ᵉ** : c'est la 3ᵉ demande
   explicite ; ne pas la faire passer derrière du structurel non demandé. *Done :*
   toggle « moyenne du prior » OFF par défaut, `1/degré` correct sans override,
   identique pour α ∈ {1,2,100}, garde-dénominateur (puits ⇒ pas de label),
   libellé « P attendue avant fit », helper partagé, YAML modèle inchangé,
   bidirectionnelles lisibles.
3. **Lot C1 (self-loops) + D1 (Tidy)** (P0, ~1,5–2 j). *Done :* self-loop créable
   et **visible** (arc) ; Tidy range left-right et ergodique, **un seul Ctrl+Z**.
4. **Lot D2/D3 + C2** (P1, ~1,5 j). *Done :* minimap + snap ; onboarding vide
   (presets == `allowedTransitionsForShape`) ; badges de lint sur les nœuds fautifs.
5. **Lot E confort** (E1/E2, ~1 j). *Done :* raccourcis (garde-focus correct),
   couleurs + légende.
6. **Lot E4 accessibilité** (~1 j, **slice séparée**) — mesurée contre
   `e2e/tests/accessibility.spec.ts` (axe-core existe déjà). *Done :* aria-labels,
   focus management, statut non-couleur-seule, connexion au clavier.

*(E3 mask grid : hors chantier. Total révisé ~7,5–8 j ; estimations larges.)*

**Tests — décision (résout la lacune de revue) :**
- **Infra unitaire** : **ajouter vitest** au frontend (il n'existe aucun runner
  unitaire JS aujourd'hui ; cf. Q6). Tests purs : `probEdgeStyle(p)`, calcul
  d'aperçu (uniforme = 1/degré ; **invariance** α∈{1,2,100} ; puits ⇒ pas de
  label), linter structurel (inatteignable/puits selon mode startprob), fonctions
  d'auto-layout. Câbler `npm test` dans `ci.yml` (le job `e2e.yml` est
  `workflow_dispatch`, ne pas en dépendre).
- **E2E Playwright** : le golden path éditeur actuel
  (`e2e/tests/topology-editor.spec.ts`) ne couvre que undo/redo + export — donc
  ce sont de **nouveaux** specs à y **ajouter** (et non « étendre » l'existant) :
  drag→reload persiste + sélection conservée ; Tidy + un seul undo ; self-loop
  créé visible ; toggle d'aperçu affiche un nombre étiqueté ; preset == shape ;
  Delete retire du canvas et du store.
- **Non-régression** : le YAML *modèle* produit est inchangé par le lot B
  (snapshot test).

## 7. Pointeurs

- Audit source (journal de session 2026-06-02) : workflow `hmm-editor-ux-audit`.
- Fichiers cœur : `EditorCanvas.tsx`, `StateNode.tsx`, `nodeTypes.ts`,
  `Toolbar.tsx`, `SidePanel.tsx`, `PerEdgePriorPanel.tsx`,
  `store/topologyStore.ts`, `lib/yaml.ts`, `lib/buildTopologyYaml.ts`.
- Renderer réutilisable : `components/results/TransmatGraph.tsx`.
- Discipline scope : [[hmm-studio-scope-discipline]],
  [[hmm-studio-distribution-strategy]].
- Roadmap : la viz topologie P1/P2 est déjà SHIPPED (cf. `docs/roadmap.md`,
  section « Travaux livrés hors-roadmap initial ») ; ce chantier en est la suite.
