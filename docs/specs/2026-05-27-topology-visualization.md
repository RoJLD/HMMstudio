# Topology visualization — arrows, transition graph, playback — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis
**Status** : SPEC DRAFTED · Phase 1 prête à implémenter (frontend-only) ; Phase 2 spec-only
**Effort estimé** : Phase 1 ~0.5j · Phase 2 ~1-1.5j

> Emplacement `docs/specs/` (convention réelle).

---

## 1. Contexte et problème

Demande : (1) montrer les transitions avec des **flèches** dans la topologie,
(2) afficher les **probabilités de transition** en bulle, (3) tracer les
**courbes des variables** observées, (4) un bouton **play** pour voir évoluer
les probabilités d'états et le chemin emprunté.

**Découverte clé (audit du code existant)** : la page Results fait déjà
beaucoup. Elle expose et visualise :
- la **matrice de transition apprise** (`getFitTransmat` → `TransmatHeatmap`) ;
- le **chemin de Viterbi** (`ViterbiTimeline`, surligne `currentT`) ;
- les **postérieurs par pas de temps** (`DecodedResponse.posterior[t]`) ;
- un **lecteur** complet (`TimelinePlayer` : ▶/pause, step, vitesse 0.5×–4×,
  scrubber) qui avance `currentT` et pilote déjà ViterbiTimeline + NHMM `A(t)`.

Donc le « play » (#4), les probabilités (#2) et le chemin existent **déjà**.
Les vrais manques :
- **#1** : les arêtes de l'éditeur n'ont **pas de flèche** (`type:"default"`,
  pas de `markerEnd`).
- une **vue graphe** de la transmat apprise (flèches + bulles + épaisseur) —
  aujourd'hui seulement un **heatmap**, pas un graphe de nœuds.
- **#3** : la **série des variables observées** n'est ni exposée ni tracée
  (le décodé donne chemin + postérieurs, pas le `X` brut).

## 2. Goal

Rendre la dynamique du modèle *lisible comme un graphe*, en **réutilisant**
l'infrastructure existante (transmat, postérieurs, `TimelinePlayer`,
`currentT`). Deux phases.

## 3. Design

### Phase 1 (frontend pur — implémentée maintenant)

**A. Flèches dans l'éditeur** (`EditorCanvas.tsx`)
- Ajouter `markerEnd: { type: MarkerType.ArrowClosed, color }` à chaque arête
  (couleur = stroke : indigo si override de prior, slate sinon). Montre la
  **direction** des transitions autorisées. Les self-loops rendent une boucle
  fléchée (persistance).

**B. Graphe de transition appris** (`components/results/TransmatGraph.tsx`, nouveau)
- Composant **lecture seule** (découplé du store topology) : un `ReactFlow`
  avec un petit nœud-pilule read-only (label = nom d'état, handles L/R), nœuds
  disposés en **cercle** (auto-layout, car la transmat n'a pas de positions).
- Une arête par `(i,j)` où `mask[i][j]` et `transmat[i][j] ≥ 0.01` :
  - **flèche** (`markerEnd` ArrowClosed),
  - **bulle** = probabilité `p.toFixed(2)` (label réutilisant le style des
    labels d'arête de l'éditeur),
  - **épaisseur** ∝ `p` (`strokeWidth = 1 + 5p`) + opacité ∝ `p`,
  - self-loops `i==j` inclus (boucle = rester dans le régime).
- `nodesConnectable=false`, `elementsSelectable=false`, `nodesDraggable=true`,
  `zoomOnScroll=false`, `fitView`. Fond `Background`.
- Branché dans `ResultsPage` (statut `done`) **en plus** du heatmap (le graphe
  pour l'intuition, le heatmap pour la précision), alimenté par le `transmat`
  déjà chargé. Aucun appel backend nouveau.

### Phase 2 (spec-only — itération suivante)

- **Animer le graphe** : passer `currentT` + `viterbi[t]` + `posterior[t]`
  (déjà dispo) au `TransmatGraph` → nœud de l'état courant **allumé**, arête
  active `viterbi[t-1]→viterbi[t]` **surlignée**, remplissage des nœuds = la
  **distribution postérieure** `posterior[t]` (les « probas d'états » qui
  évoluent). Petit, car `TimelinePlayer` + postérieurs + `currentT` existent.
- **Courbes de données (#3)** : nouvel endpoint `GET /api/fit/{id}/series`
  (ou extension du décodé) exposant la série observée `X` ; tracer les
  variables sous le graphe, synchronisées à `currentT` (curseur vertical).
  Seul morceau nécessitant du backend.

## 4. Scope boundaries

- **Phase 1 = aucun backend, aucune dépendance nouvelle** (réutilise reactflow,
  déjà présent, et `getFitTransmat`).
- On **n'enlève pas** le heatmap (complémentaire).
- On **ne réutilise pas** `StateNode` (éditable + couplé au store) — un nœud
  read-only dédié.
- Pas de toggle d'édition sur le graphe Results (lecture seule).
- Courbes de données + animation = **Phase 2** (la série `X` n'est pas exposée
  aujourd'hui).

## 5. Tests

Pas de runner JS. Validation : `npm run build` (tsc strict) + vérif manuelle
(flèches dans l'éditeur ; graphe Results avec flèches + bulles + épaisseur ∝ p ;
self-loops ; cohérent avec le heatmap).

## 6. Définition de "done" (Phase 1)

- [ ] `markerEnd` (flèches) sur les arêtes de `EditorCanvas`.
- [ ] `components/results/TransmatGraph.tsx` (read-only, layout circulaire,
      flèches + bulles + épaisseur).
- [ ] Panneau « Transition graph » dans `ResultsPage` (statut done), nourri par `transmat`.
- [ ] `npm run build` vert ; CHANGELOG `[Unreleased]`.

## 7. Open questions

1. Seuil d'affichage des arêtes (0.01) — ajustable si le graphe est trop
   chargé/clairsemé. Défaut 0.01.

## 8. Provenance

Demande utilisateur (2026-05-27) : flèches + probas en bulle + courbes de
données + play pour l'évolution des états. Audit : la majeure partie (play,
probas, chemin, postérieurs) existe déjà → phasage validé : Phase 1 = flèches
éditeur + graphe transmat statique (frontend pur) ; Phase 2 = animation via
`currentT` + courbes de données (endpoint).

## 9. Update 2026-05-27 — Phase 1 shipped

Implémenté : flèches (`markerEnd` ArrowClosed) sur les arêtes de `EditorCanvas` ;
`components/results/TransmatGraph.tsx` (graphe read-only, layout circulaire,
flèches + bulles de proba + épaisseur ∝ p, seuil 0.01, nœud read-only dédié) ;
panneau « Transition graph » dans `ResultsPage` à côté du heatmap, nourri par le
`transmat` déjà chargé. `npm run build` vert, aucun backend. Phase 2 (animation
via `currentT` + endpoint des séries pour les courbes) reste spec-only.

## 10. Update 2026-05-27 — Phase 2 shipped

Implémenté :
- **Animation du graphe** : `TransmatGraph` reçoit `decoded` + `currentT` (déjà
  fournis par `TimelinePlayer`) → état courant `viterbi[idx]` **ringé**,
  remplissage des nœuds = `posterior[idx]` (couleur d'état × proba), arête active
  `viterbi[idx-1]→viterbi[idx]` surlignée + `animated`. Mapping
  `idx = floor(currentT/step)` (comme `ViterbiTimeline`). Frontend pur.
- **Courbes de données (#3)** : nouvel endpoint `GET /api/fit/{id}/series`
  (colonnes numériques du dataset, downsamplées au **même `step`** que `/decoded`)
  + composant `DataCurves` (lignes min–max normalisées, curseur synchronisé à
  `currentT`) + panneau « Observed data » dans `ResultsPage`. Test backend
  `test_get_fit_series_done` vert ; `npm run build` vert.

Les 4 demandes initiales sont couvertes : flèches (éditeur + graphe), bulles de
proba (graphe), courbes de variables (DataCurves), et play/évolution
states-proba + chemin (graphe animé via le player existant).
