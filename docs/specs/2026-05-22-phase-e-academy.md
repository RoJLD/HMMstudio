# Phase E — Academy (apprentissage interactif intégré) : spec

**Date** : 2026-05-22
**Auteur** : Robin Denis (avec architecte-CEO framing)
**Status** : SPEC DRAFTED · gated sur V livré + B stable
**Effort estimé** : 1-2 semaines
**Prérequis** : Phase V livrée (validation scientifique), Phase B MVP stable

> Document de spec. Pour le contexte stratégique et la priorité, voir
> [docs/roadmap.md § Phase E](../roadmap.md).

---

## 1. Contexte et motivation

L'**enseignement** est l'une des trois mâchoires explicites du wedge
stratégique (cf. § Positionnement stratégique 2026 dans la roadmap).
Sa propriété unique : **leverage long-terme**. Un prof qui adopte
`hmm-studio` en TP touche 20 à 100 étudiants par an. Ces étudiants
intériorisent l'outil et le réutilisent en thèse, en industrie, en
recherche. Sur 5 ans, un seul prof acquis = 100-500 utilisateurs
secondaires.

**État aujourd'hui** : zéro contenu pédagogique intégré. Un nouveau
visiteur qui débarque sur l'éditeur de topologie voit des "matrices de
transition" et des "états cachés" sans contexte. C'est intimidant pour
quiconque n'a pas déjà suivi un cours HMM. **Trou d'acquisition pur.**

La phase E ferme ce trou avec un **MVP volontairement étroit** : 7 leçons,
1-2h de contenu total, pas plus. La philosophie est "fewer, better,
integrated" — pas un Coursera des HMM.

## 2. Périmètre

### Inclus (MVP)
- 7 leçons interactives courtes
- Onglet "Academy" dans la navigation B
- Bridge "Try in editor" : chaque leçon ouvre un YAML pré-rempli dans
  l'éditeur de topologie
- Persistance de la progression utilisateur (localStorage, pas de backend)
- URLs partageables : `/academy/lesson-3-forward-algorithm`
- Composants D3 réutilisables (probability simplex, animated path, etc.)

### Exclus (hors-MVP, gated sur signal)
- Quiz / certificats / gamification → E.2 si demande utilisateur
- Vidéos / screencasts → E.3 si bande passante content authoring le permet
- Plus de 7 leçons → E.4 (avec critères "fewer better" maintenus)
- Traduction multi-langue (français + anglais) → E.5
- Backend (analytics utilisateur, suivi détaillé) → E.6 si pivot SaaS

## 3. UX / navigation

### Placement onglet

```
Navigation actuelle (Phase B) :
[Home] [Data] [Topology editor] [Fit] [Results]

Navigation cible (Phase E) :
[Home] [Data] [Topology editor] [Fit] [Results] [Academy]
                                                  ▲
                                            position pédagogique
                                            (à droite, séparé du flow
                                             "do" qui est à gauche)
```

**Justification du placement à droite** : le flow principal du produit
(charger données → dessiner topologie → fitter → voir résultats) est de
gauche à droite. L'académie est *orthogonale* — on y va quand on veut
apprendre, pas quand on veut produire. La séparer visuellement clarifie
l'intent.

### Naming

Recommandation : **"Academy"** plutôt que "Learn" ou "Tutorial" :
- Brandé sans être prétentieux (cf. Linear Academy, Notion Academy, Vercel University)
- Suggère un parcours structuré
- Plus mémorable pour SEO / bouche-à-oreille
- À tester avec 2-3 profs avant ship final

### Structure d'une leçon

Chaque leçon a la même architecture :

```
┌─────────────────────────────────────────────────────┐
│ # Lesson title                                       │
│ Estimated time: 10-15 min · Difficulty: Beginner    │
│                                                       │
│ ## Why this matters                                  │
│ [paragraph: hook + concrete real-world example]      │
│                                                       │
│ ## Interactive demo                                  │
│ ┌─────────────────────────────────────────────────┐ │
│ │  [D3 visualization + interactive controls]       │ │
│ │  Slider, button, hover → live update            │ │
│ └─────────────────────────────────────────────────┘ │
│                                                       │
│ ## What's happening (the math, gently)              │
│ [MDX content with inline KaTeX where needed,        │
│  no walls of equations]                             │
│                                                       │
│ ## Try it yourself                                   │
│ ┌─────────────────────────────────────────────────┐ │
│ │  [Try this lesson's YAML in the editor →]      │ │
│ └─────────────────────────────────────────────────┘ │
│                                                       │
│ ## Where to go next                                  │
│ → Next lesson: [link]                                │
│ → Related: external reading (Rabiner 1989, Durbin)  │
└─────────────────────────────────────────────────────┘
```

## 4. Les 7 leçons en détail

### Leçon 1 — "Qu'est-ce qu'un état caché ?"

**Objectif d'apprentissage** : comprendre intuitivement la distinction
état latent / observation.

**Demo interactive** : pièce truquée/honnête.
- Deux pièces : "fair" (50/50) et "biased" (80/20)
- L'utilisateur clique : la pièce courante émet pile/face selon ses probs
- Mais l'utilisateur ne sait pas quelle pièce est utilisée (état caché)
- Un bouton "Reveal the hidden state" colorie a posteriori chaque flip
  avec sa pièce d'origine

**Composant** : `<HiddenStateDemo />` (à créer, ~150 LOC React + D3)

**Bridge YAML** : topologie 2 états, multinomial 2 symbols.

**Durée cible** : 10 min.

### Leçon 2 — "La matrice de transition, c'est un graphe"

**Objectif** : faire le lien graphe ↔ matrice K×K.

**Demo** : mini-éditeur 2 états (sous-set de l'éditeur full).
- Deux nœuds A et B sur un canvas
- Slider pour P(A → A), P(B → B). Les autres probas s'auto-complètent.
- À droite : la matrice 2×2 mise à jour en live
- Bouton "Sample trajectory" : simule 50 pas, affiche la séquence colorée
- Slider sur les probas → la trajectoire échantillonnée change

**Composant** : `<MiniTopologyEditor />` (réutilise StateNode existant).

**Bridge YAML** : topologie 2 états ergodique gaussienne.

**Durée cible** : 12 min.

### Leçon 3 — "Forward algorithm : pourquoi on additionne"

**Objectif** : comprendre que la prob d'une observation totale = somme sur
*tous les chemins possibles*. Insister sur **somme** vs **max** (qui sera
Viterbi en leçon 4).

**Demo** : animation belief propagation.
- 3 états, séquence de 5 observations affichée en haut
- En dessous : 3 lignes (un par état), 5 colonnes (un par t)
- L'utilisateur clique "Step" → α_t(k) calculé et affiché numériquement
- Flèches colorées montrent d'où vient chaque α
- En bas : courbe log P(X_{1:t}) qui croît

**Composant** : `<ForwardAnimation />` (D3 + animation step-by-step).

**Bridge YAML** : copie d'une topologie existante (peut être identique à L2).

**Durée cible** : 15 min.

### Leçon 4 — "Viterbi vs Forward-Backward"

**Objectif** : différence entre **most likely sequence** (Viterbi, MAP
global) et **most likely state at each t** (FB, marginales locales).
Souvent confondu par les débutants.

**Demo** : même topologie + mêmes données, deux outputs côte-à-côte.
- À gauche : séquence Viterbi colorisée
- À droite : séquence par argmax(predict_proba) à chaque t
- Mettre en valeur les positions où les deux **diffèrent** (highlight rouge)
- Toggle slider sur P(transition) bas → les deux convergent. Élevé → ils
  divergent. Insight pédagogique fort.

**Composant** : `<ViterbiVsFB />` (consomme l'API backend existante de B).

**Bridge YAML** : topologie 3 états, GMM.

**Durée cible** : 12 min.

### Leçon 5 — "Topologie : left-right vs ergodique"

**Objectif** : montrer que **la topologie n'est pas un détail**. Sur les
mêmes données, deux topologies donnent deux inférences différentes.

**Demo** :
- Données fixes (par exemple : trajectoire bruitée 4 phases)
- Bouton "Ergodic" vs "Left-right" vs "Lifecycle"
- Switcher topologie → Viterbi recompute → visualisation change
- Texte adaptatif explique pourquoi la topologie est ou n'est pas
  adaptée au type de données affichées

**Composant** : `<TopologyComparison />` + visualisation timeline.

**Bridge YAML** : topologie left-right 4 états gaussienne (l'exemple
canonique du projet).

**Durée cible** : 12 min.

### Leçon 6 — "Supervised vs Unsupervised"

**Objectif** : comprendre quand on a des labels (et donc closed-form
counting) vs pas (et donc Baum-Welch EM).

**Demo** :
- Séquence d'observations + séquence d'états annotés
- Toggle "Show labels" / "Hide labels"
- Quand labels visibles : MLE direct, transmat calculé en une passe
- Quand labels cachés : Baum-Welch EM, animation des itérations
  convergeant vers le même (ou un autre) point
- Comparer les deux : log-likelihood, transmat, viterbi
- **Insight pédagogique** : avec assez de données, les deux convergent.
  Avec peu de données, le supervised reste robuste, l'unsupervised
  peut diverger.

**Composant** : `<SupervisedComparison />` (utilise fit_supervised).

**Bridge YAML** : topologie qui démontre cas où les deux divergent.

**Durée cible** : 15 min.

### Leçon 7 — "Quand NE PAS utiliser un HMM" ⭐

**Objectif** : honnêteté intellectuelle radicale. Pointer les cas où HMM
échoue ou est sous-optimal. Distingue un outil sérieux d'un outil
commercial qui surjoue.

**Démo** : 3 datasets où HMM échoue, expliqués :

1. **Dépendance longue distance** : générer une séquence où l'observation
   à t=100 dépend de t=1 (vraie corrélation longue). Fitter un HMM →
   échec. Pointer : "ici, attention/Transformer marche mieux".

2. **Dérive continue** : générer un signal qui drift lentement sans
   transitions discrètes. Fitter un HMM → assignations erratiques.
   Pointer : "ici, Mamba/SSM ou Kalman filter marche mieux".

3. **Distribution non stationnaire** : générer un signal dont les paramètres
   d'émission *changent* dans le temps. Fitter un HMM standard → mauvais
   fit. Pointer : "ici, NHMM (voir Phase A.1 de notre projet) ou SSM
   modulaire marche mieux".

**Visualisation** : pour chaque cas, montrer le fit qui échoue, expliquer
*pourquoi*, et pointer vers l'alternative (avec link externe).

**Composant** : `<HmmLimitations />` + 3 sous-vues.

**Bridge YAML** : aucun direct, ou bien YAML d'illustration de cas-échec.

**Durée cible** : 15 min.

**Justification stratégique** : cette leçon est *critique* pour la
crédibilité. Les utilisateurs académiques détestent les outils qui
prétendent tout faire. Dire publiquement "voici nos limites" :
- gagne en crédibilité ("ils ne nous mentent pas")
- évite le mauvais usage (un user qui se rend compte que son problème
  est non-Markov ne nous blâmera pas)
- renforce le wedge en clarifiant qui on est vs qui on n'est pas

C'est aussi la leçon **anti-scope-creep** : tant qu'elle existe, on ne
peut pas pivoter vers "compile vers Mamba" sans la contredire.

## 5. Stack technique

### Choix retenu

| Composant | Choix | Justification |
|---|---|---|
| Content format | **MDX** | Markdown + composants React inline. Authoring accessible, intégration native React |
| Visualisations | **D3.js** + composants React | Standard pour les viz scientifiques, library existante riche |
| Math rendering | **KaTeX** (pas MathJax) | Plus rapide, suffisant pour notre niveau de math |
| Routing | **React Router** (déjà dans B) | Réutiliser l'infrastructure B |
| State persistence | **localStorage** | Pas besoin de backend, MVP simple |
| Reuse | Composants existants de l'éditeur B (`StateNode`, `TransmatHeatmap`, etc.) | DRY, cohérence visuelle |

### Choix rejetés

| Rejeté | Pourquoi |
|---|---|
| **Jupyter notebooks** | Nécessitent kernel + serveur, friction d'installation, cassent à chaque upgrade, mauvais bridge avec l'éditeur React |
| **Observable notebooks** | Verrouille sur Observable.com, pas auto-hébergé |
| **Pure HTML + vanilla JS** | Trop de duplication avec les composants React de B |
| **Storybook-only** | Bon pour les devs, mauvais pour les end-users |
| **PDF / slides statiques** | Pas interactif, ne sert pas le wedge |

### Structure de fichiers

```
src/hmm_studio/frontend/
├── src/
│   ├── pages/
│   │   └── academy/                           # NOUVEAU
│   │       ├── AcademyHome.tsx                # liste des leçons, progression
│   │       ├── LessonLayout.tsx               # layout commun
│   │       └── lessons/
│   │           ├── 01-hidden-state.mdx
│   │           ├── 02-transition-matrix.mdx
│   │           ├── 03-forward-algorithm.mdx
│   │           ├── 04-viterbi-vs-fb.mdx
│   │           ├── 05-topologies.mdx
│   │           ├── 06-supervised-vs-unsupervised.mdx
│   │           └── 07-when-not-to-use.mdx
│   ├── components/
│   │   └── academy/                           # NOUVEAU
│   │       ├── HiddenStateDemo.tsx            # leçon 1
│   │       ├── MiniTopologyEditor.tsx         # leçon 2
│   │       ├── ForwardAnimation.tsx           # leçon 3
│   │       ├── ViterbiVsFB.tsx                # leçon 4
│   │       ├── TopologyComparison.tsx         # leçon 5
│   │       ├── SupervisedComparison.tsx       # leçon 6
│   │       ├── HmmLimitations.tsx             # leçon 7
│   │       └── shared/                        # composants partagés
│   │           ├── ProbabilitySimplex.tsx
│   │           ├── AnimatedPath.tsx
│   │           ├── TransmatVisualizer.tsx
│   │           └── TryInEditorButton.tsx      # bridge bridge
│   └── lib/
│       └── academy/
│           ├── progress.ts                    # localStorage helpers
│           └── lesson-yamls/                  # YAML fixtures pour bridge
│               ├── lesson1.yaml
│               └── ...
```

### Dépendances nouvelles (`package.json`)

```json
"@mdx-js/react": "^3.0.0",
"@mdx-js/rollup": "^3.0.0",
"d3": "^7.8.5",
"katex": "^0.16.9",
"rehype-katex": "^7.0.0",
"remark-math": "^6.0.0"
```

## 6. Authoring workflow

Pour que Robin (ou un futur contributeur) puisse ajouter / corriger une
leçon sans tout casser :

1. Éditer le fichier `.mdx` correspondant
2. Si nouveau composant interactif : créer dans `components/academy/`
3. Si nouveau YAML bridge : ajouter dans `lib/academy/lesson-yamls/`
4. Run `npm run dev` → preview locale
5. Run test E2E Playwright `npm run test:e2e:academy` → vérifie bridges
6. Commit

Pas de DB. Pas de CMS. Pas de pipeline de build complexe. **Git = CMS.**

## 7. Critères de succès / kill criteria

### Métriques à monitorer (à M+1, M+3, M+6)

| Métrique | Mode mesure | Seuil M+3 |
|---|---|---|
| Visites uniques /mois sur `/academy/*` | Plausible Analytics (à intégrer) | ≥ 100 |
| Taux de completion leçon 1 | Plausible event + localStorage | ≥ 30 % |
| Utilisations bridge "Try in editor" | Plausible event | ≥ 10 /mois |
| Profs identifiés qui l'utilisent | Outreach manuel (interviews) | ≥ 1 confirmé |
| Mentions externes | Recherche Google + Twitter + Reddit | ≥ 3 |

### Kill criteria

Si à **M+3** : (Visites < 30 /mois) ET (zéro prof identifié) ET (Robin ne
recommande pas l'académie à ses propres collaborateurs) → **archiver
l'académie en lecture seule**, ne plus investir, libérer le slot de
navigation.

C'est dur mais nécessaire. Sinon on traîne du code mort.

### Critères de re-investissement (E.2+)

Si à M+3 les seuils sont atteints : autorisation à investir en E.2
(quiz / certificats) ou E.3 (vidéos). Mais **pas avant**.

## 8. Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Scope creep ("ajoutons 20 leçons", "ajoutons un LMS") | Élevée | Strict : MVP = 7 leçons exactement. Toute extension va en E.2/E.3 avec gating |
| Mauvais ton pédagogique (trop académique ou trop bébé) | Moyenne | Faire relire les 7 leçons par 2-3 profs avant ship. Itérer si feedback |
| Contenu se périme quand l'éditeur évolue (B.x) | Moyenne | Tests E2E Playwright sur chaque bridge "Try in editor" → CI détecte régression |
| Adoption nulle malgré qualité du contenu | Élevée | Outreach manuel post-ship : poster sur Reddit r/MachineLearning, r/learnmachinelearning, Hacker News, Twitter académique. Pas de magie : il faut faire connaître |
| Bug pédagogique (math fausse dans une leçon) | Moyenne | Tous les exemples doivent passer par les tests V (validation suite). Pas de "trust me" sur les valeurs numériques |
| Maintenance burden des composants D3 | Moyenne | Limiter à 7 composants spécifiques + 3-4 partagés. Ne pas en faire une lib |

## 9. Définition de "done" pour E (MVP)

- [ ] 7 leçons .mdx complètes, relues par ≥ 2 profs externes
- [ ] 7 composants interactifs spécifiques + 3-4 partagés
- [ ] Onglet "Academy" dans la navigation
- [ ] Bridge "Try in editor" fonctionnel pour les 7 leçons (test E2E Playwright)
- [ ] Persistence progression utilisateur via localStorage
- [ ] URLs partageables `/academy/[slug]`
- [ ] Plausible Analytics intégré sur les pages `/academy/*`
- [ ] Section "Academy" ajoutée au README et au site mkdocs
- [ ] Annonce écrite (blog post, Twitter thread) prête à publier
- [ ] ADR-0007 sur le choix MDX vs Jupyter

## 10. Successeurs probables (E.2+ hors-scope)

Listés ici pour documenter la **discipline anti-scope-creep** :
elles sont *gated sur signal externe à M+3*, pas avant.

- **E.2** : Quiz + certificat de complétion (LinkedIn-shareable)
- **E.3** : Vidéos / screencasts par leçon (5-10 min)
- **E.4** : Leçons avancées (HMM hiérarchique, NHMM avancé, switching SSM)
- **E.5** : Internationalisation (FR + EN minimum)
- **E.6** : Backend analytics (suivi utilisateur détaillé, A/B testing)
- **E.7** : "Class mode" — profs créent une cohorte d'étudiants, suivent leur progression
- **E.8** : Intégration LMS (Canvas, Moodle, Blackboard) — gated sur ≥ 3 profs confirmés

Aucune de ces extensions n'est promise. Toutes attendent un signal réel.

## 11. ADR à créer

`docs/decisions/0007-academy-stack-mdx-vs-jupyter.md` :
- Pourquoi MDX et pas Jupyter ?
- Pourquoi 7 leçons et pas plus / pas moins ?
- Pourquoi onglet séparé et pas contextuel ?
- Pourquoi localStorage et pas backend ?
- Comment ajouter une leçon sans casser le système ?
