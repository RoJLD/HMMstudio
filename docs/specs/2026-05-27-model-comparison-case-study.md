# Model-comparison case-study lesson + /compare framing — design spec

**Date** : 2026-05-27
**Auteur** : Robin Denis
**Status** : SPEC DRAFTED · prêt à implémenter (1 phase, frontend-only)
**Effort estimé** : ~0.5 jour
**Crédit** : s'appuie sur la recherche de Nathan Berbinau
(<https://github.com/NathanBerbinau>) — cf. `CONTRIBUTORS.md`.

> Emplacement `docs/specs/` (convention réelle). Divergence connue avec le
> `CLAUDE.md` local (`docs/superpowers/specs/`), non tranchée.

---

## 1. Contexte et problème

hmm-studio sait désormais *comparer* des modèles (`/compare`, `hmm-fit compare`,
HQIC) et *enseigner* les variantes (Academy). Mais aucune leçon ne traite du
**jugement** : *quand* la complexité vaut le coût, et le piège de
**comparabilité** (on ne compare pas des log-vraisemblances entre familles de
modèles différentes).

La recherche de Nathan fournit une **étude de cas honnête** parfaite : sur ses
données crypto, un GMM-HMM simple bat des variantes plus sophistiquées (NHMM),
une extension custom (Skew-T) *dégrade* les résultats, et la log-vraisemblance
du rSLDS n'est même pas comparable (espace latent différent). Y compris ses
réserves (métrique non définie, un seul dataset, pas d'IC) — qui *sont* la
leçon.

## 2. Goal

Une leçon Academy qui utilise cette étude de cas pour enseigner la comparaison
de modèles **honnête**, + une note de comparabilité sur la page `/compare`
(là où la comparaison se fait), créditant Nathan. **Aucun code de modèle porté**
(rSLDS / Skew-T / dcor restent hors scope) ; on réutilise les *enseignements*,
pas les modèles.

## 3. Design

### A. Nouvelle leçon — `lesson-14-comparing-models`

- Catégorie **`selection`** (Bayesian & model choice), `order: 3` (après
  bayesian=1, choosing-features=2) → étape globale 14. Difficulté **Advanced**.
- Composant `lessons/lesson-14-comparing-models.tsx`, entrée dans
  `lessons/index.ts`.
- **Contenu** (4 points, qualitatif — *pas* de chiffres cités comme faits) :
  1. **Benchmarke, ne suppose pas.** Toujours comparer des candidats sur un
     critère, pas à l'intuition.
  2. **Le plus simple gagne souvent.** Étude de cas : un GMM-HMM a battu un NHMM
     plus riche — plus de paramètres ≠ meilleur.
  3. **La complexité doit payer (les résultats négatifs comptent).** Une
     extension custom (Skew-T) a *dégradé* le fit — un résultat négatif est une
     vraie information.
  4. **On ne compare pas n'importe quoi.** Log-vraisemblances non comparables
     entre familles : un NHMM conditionne sur des covariables (`P(X|Z)`), un
     rSLDS vit dans un espace latent continu. → **c'est pourquoi `/compare`
     marque `comparable=False`** et ne classe que les modèles `P(X)`.
  - Encadré crédit : « Case study adapted from Nathan Berbinau's crypto
    regime-detection research (github.com/NathanBerbinau). »
  - `FurtherReading` : repo de Nathan + (option) Giudici 2020.
  - Pas de `presetTopologyYaml` ; à la place un lien **« Compare models →
    /compare »** (texte/CTA) — la leçon pointe vers l'outil qui opérationnalise
    son propos.
- **Quiz + deck** : ajouter une entrée `lesson-14-comparing-models` à
  `LESSON_QUIZZES` (~3 cartes + ~3 QCM ; niveaux Recall/Apply/Analyze ; les
  questions portent sur les 4 points, en particulier la comparabilité).

### B. Framing sur `/compare` (`ComparePage`)

- Ajouter une **note de comparabilité** courte sur la page : « Only models of
  `P(X)` (Gaussian/GMM/Poisson) are directly comparable by BIC/AIC/HQIC.
  NHMM (P(X|Z)) and Factorial models live on a different scale — that's why
  they're not in this grid. » + lien vers la leçon
  `/academy/lesson-14-comparing-models` (« Why? — read the case study »).
- La page exclut déjà NHMM/Factorial du grid ; la note **explique le pourquoi**
  et relie au cours.

### C. Crédit
- Inline dans la leçon (encadré ci-dessus) ; déjà dans `CONTRIBUTORS.md`.

## 4. Scope boundaries

- **Aucun modèle porté** (rSLDS, Skew-T `ssm`, dcor) — hors scope HMM.
- **Aucun chiffre de benchmark cité comme fait** — métrique « LP normalisée »
  non définie, un seul dataset, pas d'IC, LL non comparable inter-familles. On
  enseigne la *méthode* + les *réserves*, qualitativement.
- **Pas de wizard** touché (la création n'est pas la comparaison ; le lien
  utile est leçon → `/compare`).
- **Pas de backend** — frontend pur.

## 5. Tests

Pas de runner JS. Validation : `npm run build` (tsc strict) + vérif manuelle
(leçon 14 rendue dans la section *selection*, étape 14 ; quiz/deck OK ; note +
lien sur `/compare`).

## 6. Définition de "done"

- [ ] `lesson-14-comparing-models.tsx` + entrée `index.ts` (selection, order 3, Advanced).
- [ ] Entrée `LESSON_QUIZZES["lesson-14-comparing-models"]` (deck + quiz).
- [ ] Note de comparabilité + lien vers la leçon sur `ComparePage`.
- [ ] Crédit Nathan inline ; `npm run build` vert ; CHANGELOG `[Unreleased]`.

## 7. Open questions

1. Lien leçon→/compare : simple `<Link to="/compare">` (CTA) — OK, pas de
   nouveau mécanisme. Confirmé.

## 8. Provenance

Demande utilisateur (2026-05-27) : réutiliser les leçons + résultats de Nathan
pour l'Academy / le wizard / hmm-studio, et le créditer. Direction validée :
leçon étude-de-cas + framing `/compare`. Réutilisation des *enseignements*
(méthodologie + réserves honnêtes), pas des modèles hors-scope.

## 9. Update 2026-05-27 — shipped

Implémenté : leçon `lesson-14-comparing-models` (catégorie `selection`, order 3,
Advanced) + deck/quiz dans `LESSON_QUIZZES`, note de comparabilité + lien vers la
leçon sur `ComparePage`, crédit Nathan inline + dans `CONTRIBUTORS.md`.
`npm run build` vert. Conforme au scope : aucun modèle porté
(rSLDS/Skew-T/dcor restent hors-wedge), aucun chiffre de benchmark cité comme
fait — l'étude de cas est qualitative.
