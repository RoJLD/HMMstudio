# Parameter help tooltips ("?" with explanation + course link) — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis
**Status** : SPEC DRAFTED · prêt à planifier (1 phase)
**Effort estimé** : ~1-1.5 jour (composant + registry + câblage 3 surfaces)
**Prérequis** : Academy lessons 1-13 (livrées) — fournissent les cibles des liens « Learn more ».

---

## 1. Contexte et problème

Configurer une topology demande de savoir ce que fait chaque paramètre :
`covariance_type`, `n_iter`, `tol`, `α (Dirichlet)`, `init.strategy`,
`n_features`… Aujourd'hui l'éditeur n'offre **aucune aide en place** : un
nouvel utilisateur doit quitter l'écran pour lire les docs ou l'Academy,
puis revenir. Ça :

- relève la barrière au premier fit réussi,
- déconnecte l'Academy (qu'on vient d'enrichir : 13 leçons + biblio) de
  l'endroit où l'utilisateur configure réellement les modèles.

## 2. Goal

Chaque champ de paramètre, sur **toutes les surfaces de configuration**
(éditeur de topology, page Fit, page Data prep), porte un petit `?` qui
ouvre une explication concise et, quand c'est pertinent, un lien profond
vers la leçon Academy correspondante — pour **apprendre ET configurer au
même endroit**.

## 3. Design

### Décisions validées (2026-05-27)
- **Interaction** : **click popover** (pas hover). Un clic sur `?` ouvre un
  petit panneau ancré ; il reste ouvert (donc il peut porter un lien
  cliquable « Learn more »), se ferme sur Échap / clic-extérieur / re-clic.
  Marche au tactile et au clavier.
- **Portée v1** : **toutes les surfaces de saisie** — éditeur + Fit + Data prep.
- **Liens cours** : on lie **uniquement** les paramètres qui ont une leçon
  clairement pertinente ; les autres ont juste l'explication.

### Composant `<HelpTip>`

```tsx
// src/hmm_studio/frontend/src/components/help/HelpTip.tsx
interface HelpTipProps {
  paramKey: string;   // clé dans PARAM_HELP
  className?: string;  // positionnement optionnel
}
export function HelpTip({ paramKey }: HelpTipProps): JSX.Element | null
```

- Rend un bouton `?` discret (slate, brand au hover) à côté du label du champ.
- Clic → toggle un popover ancré (div absolu positionné près du bouton).
- Popover : **titre**, **corps** (1-3 phrases), et si l'entrée a `lesson`,
  un lien `Learn more → <label>` (react-router `<Link to={"/academy/" + id}>`).
- A11y : bouton `aria-label="Help: <titre>"`, popover `role="dialog"`/`tooltip`,
  focus déplacé dans le popover à l'ouverture, Échap referme et rend le focus,
  fermeture sur clic-extérieur (listener `mousedown` global pendant l'ouverture).
- Si `paramKey` est absent du registry → le composant ne rend **rien**
  (`return null`) : pas de `?` orphelin.

### Registry de contenu (source unique)

```ts
// src/hmm_studio/frontend/src/components/help/paramHelp.ts
export interface ParamHelpEntry {
  title: string;
  body: string;                       // texte court, anglais (cohérent UI)
  lesson?: { id: string; label: string };  // id = lesson-x-... ; label affiché
}
export const PARAM_HELP: Record<string, ParamHelpEntry> = { ... };
```

Copie **découplée** des composants de formulaire : un seul fichier à
maintenir, réutilisable partout où le paramètre apparaît. Les composants
n'écrivent que `<HelpTip paramKey="fit.n_iter" />`.

### Clés de paramètres + mapping leçon (initial)

| paramKey | Surface | Leçon liée |
|---|---|---|
| `topology.name` | éditeur | — |
| `emission.type` | éditeur | lesson-1-what-is-an-hmm (overview) |
| `emission.n_features` | éditeur | lesson-13-choosing-features |
| `emission.covariance_type` | éditeur | lesson-5-baum-welch |
| `emission.n_mix` (gmm) | éditeur | lesson-8-gmm-hmm |
| `emission.n_symbols` (multinomial) | éditeur | lesson-2-markov-chains |
| `init.strategy` | éditeur | lesson-5-baum-welch |
| `init.seed` | éditeur | — (reproductibilité) |
| `fit.n_iter` | éditeur | lesson-5-baum-welch |
| `fit.tol` | éditeur | lesson-5-baum-welch |
| `priors.alpha` | éditeur | lesson-10-bayesian-hmm |
| `topology.allowed_transitions` | éditeur | lesson-6-constrained-topologies |
| `scan.k_range` | Fit | (K-scan : pas de leçon dédiée → —) |
| `scan.seed` | Fit | — |
| `data.<param>` | Data prep | à confirmer (cf. open question 1) |

Les clés `data.*` exactes dépendent des contrôles réels de la page Data prep
— à figer en lisant la page au moment du plan.

### Surfaces câblées (v1)

1. **Éditeur de topology** (panneau de gauche, cf. capture) : Name, Type,
   n_features, covariance, Strategy, Seed, n_iter, tol, α, allowed_transitions.
2. **Page Fit** : k_min/k_max (k_range), seed, mode scan.
3. **Page Data prep** : les paramètres de ses contrôles (recettes/ops prep).

### Positionnement / styling
- Popover ~260px, fond blanc, bordure slate, ombre légère, petit texte —
  palette existante. Positionné en absolu relativement au `?` (pas de
  nouvelle dépendance lourde ; popover fait-main). Si le positionnement
  devient pénible (débordement de viewport), revoir (open question 3).

## 4. Scope boundaries (ce qu'on ne fait PAS)

- **Pas de contenu riche** (image/vidéo) en v1 — texte + un lien leçon.
- **Pas de `?` sur les pages de résultats** (Results, Scan results) : ce sont
  des affichages en lecture seule, pas de la configuration.
- **Pas d'i18n** en v1 — copie en anglais, cohérent avec le reste de l'UI.
- **Pas un tour d'onboarding** — aide discrète par-paramètre seulement.
- **Aucun changement backend** — purement frontend.

## 5. Tests

Le frontend **n'a pas de runner de tests JS** (scripts : dev/build/preview/
`lint = tsc --noEmit` ; pas de `test`). Conformément à la règle CI/CD du
workspace (« si aucune infra de test n'existe, signaler le manque plutôt que
d'en inventer une pour une feature »), la validation v1 passe par :

- `npm run build` (tsc strict + bundle) vert — y compris la résolution des
  types du registry et du composant.
- Vérification manuelle : `?` présent sur chaque champ ciblé, popover
  s'ouvre/ferme (clic, Échap, clic-extérieur), lien leçon navigue vers
  `/academy/<id>`.

> ⚠️ Gap signalé : pas de test unitaire frontend pour `HelpTip`. Si une infra
> de test JS (Vitest + Testing Library) est introduite plus tard, ajouter un
> test `HelpTip` (rend `?`, ouvre au clic, affiche le corps, rend le lien
> quand `lesson` présent, ferme sur Échap). Hors scope de cette feature
> d'introduire le runner.

## 6. Définition de "done"

- [ ] `HelpTip.tsx` + `paramHelp.ts` créés ; `PARAM_HELP` couvre les clés ci-dessus.
- [ ] `?` câblé sur les 3 surfaces (éditeur, Fit, Data prep).
- [ ] Popover accessible (Échap / clic-extérieur / focus), lien leçon fonctionnel.
- [ ] `npm run build` vert ; bundle reconstruit.
- [ ] (Doc) mention dans CHANGELOG `[Unreleased]`.

## 7. Open questions (à résoudre pendant le plan)

1. **Paramètres Data-prep exacts** à couvrir — dépend des contrôles actuels
   de la page Data ; à figer en lisant la page au début du plan.
2. **`emission.type`** : un seul lien overview (lesson-1 / lesson-5) ou un
   lien dépendant du type sélectionné ? Défaut : entrée unique → lesson-1.
3. **Implémentation du popover** : fait-main vs petite lib. Défaut : fait-main
   (zéro nouvelle dépendance) ; revoir si le positionnement déborde du viewport.

## 8. Provenance

Demande utilisateur (2026-05-27) : « Pourrait-on mettre des "?" (pour
joindre des infos + redirection si besoin vers un cours) à côté de chaque
paramètre ? Permettrait de comprendre/apprendre et configurer rapidement. »
Décisions interaction (click popover) + portée (toutes surfaces) validées le
même jour.
