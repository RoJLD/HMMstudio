# Academy lesson organization — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis
**Status** : SPEC DRAFTED · prêt à implémenter (1 phase, frontend-only)
**Effort estimé** : ~0.5 jour

> Note d'emplacement : ce spec vit dans `docs/specs/` comme tous les specs
> existants du projet (model-variant-selection, unsupervised-feature-selection,
> parameter-help-tooltips). Le `CLAUDE.md` local mentionne
> `docs/superpowers/specs/` — divergence connue, non tranchée ici ; on suit la
> convention réelle en place.

---

## 1. Contexte et problème

Les 13 leçons de l'Academy s'affichent dans **une seule grille plate**
(`AcademyPage.tsx`), dans l'ordre du tableau `LESSONS`. Chaque carte porte un
badge de difficulté, mais il n'y a **aucun regroupement thématique ni ordre
explicite**. L'ordre marche pour les leçons 1–10 (montée Beginner→Advanced),
mais les leçons ajoutées ensuite **cassent la progression** : L11
Semi-supervised (Intermediate), L12 Hierarchical (Advanced), L13 Choosing
features (Intermediate) sont collées à la fin, hors séquence.

Résultat : un nouveau venu ne voit pas de parcours clair, et les leçons
proches (ex. les 3 variants d'émission) sont éparpillées.

## 2. Goal

Donner à l'Academy une structure lisible : **sections thématiques** +
**numéro d'étape global** sur chaque carte. L'utilisateur voit à la fois
*par sujet* (Foundations, Inference, …) et *dans quel ordre* lire. Aucune
leçon n'est supprimée ; c'est purement de l'organisation + rendu.

## 3. Design

### Métadonnées (lessons/index.ts)

Ajouter à `LessonMeta` :

```ts
category: LessonCategory;  // union de string-literals
order: number;             // ordre AU SEIN de la catégorie (petit entier)
```

et une constante ordonnée :

```ts
export type LessonCategory =
  | "foundations" | "inference" | "learning"
  | "structure" | "variants" | "selection";

export const CATEGORIES: { id: LessonCategory; title: string }[] = [
  { id: "foundations", title: "Foundations" },
  { id: "inference",   title: "Inference" },
  { id: "learning",    title: "Learning" },
  { id: "structure",   title: "Structure & topology" },
  { id: "variants",    title: "Emission variants" },
  { id: "selection",   title: "Bayesian & model choice" },
];
```

### Taxonomie (catégorie, ordre interne) → étape globale

| Lesson | Catégorie | order | étape |
|---|---|---|---|
| lesson-1 What is an HMM? | foundations | 1 | 1 |
| lesson-2 Markov chains | foundations | 2 | 2 |
| lesson-3 Forward algorithm | inference | 1 | 3 |
| lesson-4 Viterbi | inference | 2 | 4 |
| lesson-5 Baum-Welch | learning | 1 | 5 |
| lesson-11 Semi-supervised | learning | 2 | 6 |
| lesson-6 Constrained topologies | structure | 1 | 7 |
| lesson-12 Hierarchical HMM | structure | 2 | 8 |
| lesson-8 GMM-HMM | variants | 1 | 9 |
| lesson-7 NHMM | variants | 2 | 10 |
| lesson-9 Factorial NHMM | variants | 3 | 11 |
| lesson-10 Bayesian HMM | selection | 1 | 12 |
| lesson-13 Choosing features | selection | 2 | 13 |

L'**étape globale n'est PAS stockée** : elle est calculée par `AcademyPage`
(parcours de `CATEGORIES` dans l'ordre, puis lessons triées par `order`),
donc robuste aux ajouts/réordonnancements futurs.

### Rendu (AcademyPage.tsx)

- Garder l'en-tête + le compteur "X published / completed".
- Remplacer la grille plate par une boucle sur `CATEGORIES` : chaque catégorie
  non-vide = une `<section>` avec un titre (uppercase, slate-500) + une grille
  2 colonnes des cartes de cette catégorie, triées par `order`.
- Pré-calculer `stepById` (Map id→numéro) à partir de l'ordre aplati, et passer
  `step` à chaque `LessonCard`.

### Rendu (LessonCard.tsx)

- Nouvelle prop optionnelle `step?: number`.
- Préfixer le titre d'un petit numéro discret (`{step}.` en slate-400 mono).

## 4. Scope boundaries (ce qu'on ne fait PAS)

- **Pas de nouvelle leçon** (ex. "Comparing models" lié à `/compare`) — futur,
  hors scope ; la catégorie `selection` lui laisse une place naturelle.
- **Pas de filtre/onglets par catégorie** ni de tri interactif — sections
  statiques v1.
- **Pas de changement de la page leçon** (`/academy/:id`) ni du contenu.
- **Pas de changement backend** — frontend pur.
- **Pas de réindexation par difficulté** — les catégories sont thématiques ;
  le badge de difficulté reste par carte.

## 5. Tests

Pas de runner JS (cf. specs précédents). Validation : `npm run build` (tsc
strict) vert + vérif manuelle (sections dans le bon ordre, numéros 1→13
contigus, cartes cliquables). Gap test unitaire signalé, comme pour HelpTip.

## 6. Définition de "done"

- [ ] `LessonMeta` gagne `category` + `order` ; `CATEGORIES` + `LessonCategory` exportés.
- [ ] Les 13 leçons taguées selon la table ci-dessus.
- [ ] `AcademyPage` rend des sections ordonnées avec numéros d'étape calculés.
- [ ] `LessonCard` affiche le numéro d'étape.
- [ ] `npm run build` vert ; CHANGELOG `[Unreleased]` mis à jour.

## 7. Open questions

1. Ordre interne des variants d'émission : retenu GMM → NHMM → Factorial
   (du plus proche de l'émission vanilla au plus structurel). Révisable.
2. Une future leçon "Comparing models" (catégorie `selection`) — à proposer
   séparément quand on documentera `/compare`.

## 8. Provenance

Demande utilisateur (2026-05-27) : « Mettre un ordre aux leçons ? les
organiser par thème ou catégorie ? » → délégation (« fais ce que tu penses le
mieux ») → option retenue : **sections thématiques + numéro d'étape global**.
