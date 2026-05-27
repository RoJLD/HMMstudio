# Academy quiz & flashcards — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis
**Status** : SPEC DRAFTED · prêt à planifier (1 phase, frontend-only)
**Effort estimé** : ~2-2.5 jours (engine ~1j, contenu 13 leçons ~1-1.5j)

> Emplacement `docs/specs/` (convention réelle). Divergence connue avec le
> `CLAUDE.md` local (`docs/superpowers/specs/`), non tranchée.

---

## 1. Contexte et problème

L'Academy (13 leçons, sections thématiques, tooltips `?`) **enseigne mais ne
teste pas**. Rien ne permet à l'apprenant de vérifier sa compréhension, d'avoir
un score, ni de savoir *où* il a des lacunes. La boucle d'apprentissage est
incomplète : lire → (rien) → supposer qu'on a compris.

## 2. Goal

Fermer la boucle : à la fin de chaque leçon, un **deck de flashcards** (révision
libre) **et** un **quiz QCM noté** (objectif). Le quiz donne un **score**, le
décompose **par niveau cognitif** (Recall / Apply / Analyze), et **identifie les
lacunes** (concepts ratés + lien « revoir la leçon »). Les résultats persistent
localement. Couverture : **les 13 leçons** (version lean).

## 3. Design

### Décisions validées (2026-05-27)
- **Format : hybride** — deck de flashcards (flip + auto-évaluation) ET quiz QCM
  noté, par leçon.
- **Niveaux : cognitifs par question** (Recall / Apply / Analyze) — axe
  diagnostic principal ; la difficulté de la leçon (Beginner/Int/Advanced) est
  **héritée** comme contexte (badge), pas re-taguée. Pas d'axe Easy/Med/Hard
  séparé (redondant).
- **Portée : les 13 leçons**, lean (~3-4 cartes + ~3-4 questions chacune).

### Modèle de données (`src/.../academy/lessonQuiz.ts`)

```ts
export type CogLevel = "Recall" | "Apply" | "Analyze";

export interface Flashcard {
  front: string;          // prompt
  back: string;           // réponse
  level: CogLevel;
}

export interface QuizQuestion {
  prompt: string;
  options: string[];      // 3-4 choix
  correct: number;        // index de la bonne réponse
  level: CogLevel;
  explanation: string;    // pourquoi — affiché après réponse
  concept: string;        // tag court pour le rapport de lacunes
}

export interface LessonQuiz {
  flashcards: Flashcard[];
  questions: QuizQuestion[];
}

export const LESSON_QUIZZES: Record<string, LessonQuiz>; // clé = lesson id
```

Registre unique, découplé des composants — comme `paramHelp`. Ajouter du contenu
= éditer ce fichier (data), aucune logique à toucher.

### Cœur pur et testable (`src/.../academy/scoreQuiz.ts`)

```ts
export interface QuizResult {
  total: number;
  correct: number;
  byLevel: Record<CogLevel, { correct: number; total: number }>;
  missedConcepts: string[];   // concepts des questions ratées (dédupliqués)
}
export function scoreQuiz(
  questions: QuizQuestion[],
  answers: (number | null)[],
): QuizResult;
```

Fonction pure → unité de test idéale (si Vitest un jour).

### Composants

- `components/academy/Flashcard.tsx` — carte flip (front → back au clic), badge niveau.
- `components/academy/StudyDeck.tsx` — parcourt les flashcards (prev/next/flip,
  compteur « 3/5 »).
- `components/academy/LessonQuiz.tsx` — présente les QCM (une par une ou liste),
  capture les réponses, **submit** → `scoreQuiz` → écran de résultat : score
  global, barre par niveau cognitif, explications par question, **lacunes**
  (concepts ratés) + bouton « Revisit this lesson ». Bouton « Retry ».
- Section **« Check your understanding »** en bas de `LessonPage` : deux onglets
  / boutons — *Study deck* | *Take quiz* (rendus seulement si la leçon a une
  entrée dans `LESSON_QUIZZES`).

### Persistance (`academyStore` → version 2)

Étendre le store (migration v1→v2) :
```ts
quizResults: Record<string, {        // clé = lesson id
  bestCorrect: number; total: number;
  byLevel: Record<CogLevel,{correct:number;total:number}>;
  missedConcepts: string[];
  at: string;                          // ISO date du meilleur essai
}>;
recordQuizResult: (lessonId, result) => void;  // garde le meilleur score
```
Migration : `version: 2`, `migrate` ajoute `quizResults: {}` aux états v1.

### UX « score à la fin » + suivi

- L'écran de résultat du quiz montre score + niveaux + lacunes (cf. ci-dessus).
- **Léger** : la `LessonCard` (page Academy) affiche le meilleur score si la
  leçon a été quizzée (ex. petit badge « Quiz 4/5 »), pour le suivi de progrès.

## 4. Scope boundaries (ce qu'on ne fait PAS)

- **Pas de quiz adaptatif / spaced-repetition** (pas d'algorithme SM-2) en v1 —
  deck = révision simple, quiz = noté one-shot + retry.
- **Pas de génération de questions par LLM** — contenu authoré à la main,
  vérifié (l'exactitude prime dans un outil pédagogique).
- **Pas de backend / pas de compte** — tout en localStorage (comme la
  progression actuelle).
- **Pas de timer / classement / gamification** au-delà du score.
- **Pas de types de questions autres que QCM/vrai-faux** en v1 (pas de saisie
  libre, pas de numérique).

## 5. Tests

Pas de runner JS (cf. specs précédents). Validation : `npm run build` (tsc
strict) + vérif manuelle (deck flip, quiz scoring, breakdown par niveau,
lacunes + lien, persistance du meilleur score, badge sur la carte).

> ⚠️ Gap : `scoreQuiz` est pur → test unitaire idéal si Vitest est introduit
> (score, byLevel, missedConcepts). Hors scope d'ajouter le runner.

## 6. Définition de "done"

- [ ] `lessonQuiz.ts` (modèle + `LESSON_QUIZZES` pour les **13** leçons, lean).
- [ ] `scoreQuiz.ts` (pur).
- [ ] `Flashcard`, `StudyDeck`, `LessonQuiz` composants.
- [ ] Section « Check your understanding » sur `LessonPage`.
- [ ] `academyStore` v2 (migration) + `recordQuizResult` ; badge score sur `LessonCard`.
- [ ] `npm run build` vert ; CHANGELOG `[Unreleased]` mis à jour.

## 7. Open questions

1. **Exactitude du contenu** : les 13 quiz doivent être techniquement justes.
   Authorés à partir du contenu existant des leçons ; à relire au checkpoint.
2. **Présentation du quiz** : toutes les questions sur une page (scroll) vs une
   par une. Défaut proposé : **une liste** (simple, on répond puis submit) —
   révisable à l'impl.

## 8. Provenance

Demande utilisateur (2026-05-27) : « Rajouter des flashcards à la fin de chaque
cours et selon plusieurs niveaux à academy pour tester la compréhension ?
Donner un score à la fin et identifier les lacunes ? ». Décisions (hybride
deck+quiz ; niveaux cognitifs + difficulté héritée ; 13 leçons lean ; score +
rapport de lacunes par niveau) validées le même jour.
