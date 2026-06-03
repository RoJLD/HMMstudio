---
Status: current
---

# Academy : leçon 14 corrigée + nouvelle leçon 15 « Choosing the emission distribution »

*Spec écrite le 2026-05-28. Sous-projet **B** de la réutilisation du travail de Nathan
dans hmm_studio (voir le découpage A/B/C/D dans le projet voisin
`Experiment.Crypto.2026S1.NathanBerbinau`). A (re-benchmark rigoureux) est livré et a
produit les résultats sur lesquels s'appuient ces leçons. C (option dcor) et D
(backend rSLDS) restent indépendants.*

## 1. Contexte / problème

La leçon 14 (« Comparing models honestly ») cite explicitement le travail de Nathan
et s'appuie sur des affirmations qui **ne sont plus vraies** après le re-benchmark
rigoureux livré dans `Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/benchmark/`:

- « a plain GMM-HMM outperformed a more elaborate non-homogeneous HMM (NHMM) » →
  faux. L'ancienne table mélangeait deux bibliothèques (`hmmlearn` vs `ssm`), utilisait
  K=2 pour le GMM-HMM contre K=3 pour les autres, et une normalisation par observation
  appliquée à la main hors script. Un re-benchmark *apples-to-apples* (une seule lib
  `ssm`, K identique, CV temporelle, 4 features fixes) montre une histoire différente.
- « Skew-T degraded the fit relative to a plain Student-t » → **reste vrai** dans le
  re-benchmark.

Par ailleurs, le résultat fort du re-benchmark — **l'émission domine, pas la
non-homogénéité des transitions** — mérite sa propre leçon dans la catégorie
« selection ». Aujourd'hui aucune leçon n'aborde directement le choix de la famille
d'émission, hors la leçon 8 (GMM-HMM) qui se concentre sur le cas multimodal et
n'aborde pas le diagnostic.

## 2. Objectif

Aligner la leçon 14 sur les résultats vérifiés du re-benchmark (corriger ce qui est
faux, conserver ce qui reste valide, renforcer la section méthodologique). Ajouter une
leçon 15 *diagnostic-first* qui apprend au lecteur comment savoir que son émission est
mauvaise, quels remèdes sont disponibles dans hmm_studio aujourd'hui (GMM-HMM), et ce
qui existe au-delà avec une recommandation sourcée.

## 3. Design

### 3.1 Mise à jour de `lesson-14-comparing-models.tsx`

Modifications ciblées, format inchangé (TSX + Tailwind, `FurtherReading` final) :

- **Section « The simplest model often wins »** : remplacer l'affirmation
  « GMM-HMM outperformed NHMM » par la formulation corrigée :
  *« the case study's headline claim — that a plain GMM-HMM outperformed a non-homogeneous
  HMM — did not survive an apples-to-apples re-benchmark. The original comparison mixed
  two libraries, used K=2 for the GMM-HMM but K=3 for the others, and a hand-applied
  per-sample normalization that was not in any script. A clean re-run (single library,
  same K, same features, time-series CV) showed the parsimony lesson holds — but on a
  different axis than originally claimed: it's the **emission distribution** that
  dominates (heavy-tailed Student-T beats Gaussian by orders of magnitude on held-out
  log-likelihood), while **non-homogeneous transitions add essentially nothing** over
  the homogeneous Student-T HMM. »*
- **Section « Complexity must pay — and negative results count »** : conserver
  textuellement (résultat Skew-T toujours valide), juste mentionner que le re-benchmark
  l'a confirmé indépendamment.
- **Section « You can't compare everything »** : ajouter un paragraphe court qui
  mentionne quatre pièges concrets *vus dans le case study original* et corrigés :
  (a) mélanger deux bibliothèques (différentes conventions de vraisemblance),
  (b) comparer in-sample vs hold-out,
  (c) normaliser à la main hors script,
  (d) évaluer la log-densité prédictive sous une hypothèse gaussienne pour des modèles
  à queue lourde (mésmodélise les queues → métrique non comparable).
- **Encart « Case study credit »** : remplacer le lien GitHub par un pointeur vers le
  benchmark corrigé (`Projet_Robin/benchmark/` et son README mis à jour). Reformuler :
  *« We reuse the methodology, the **honest re-benchmark**, and its **corrected**
  negative results — not the out-of-scope models. »*
- **Bas de page** : ajouter une mention « See also: Lesson 15 — Choosing the emission
  distribution » avec `<Link>` vers `/academy/lesson-15-choosing-emission`.

Aucun changement à `index.ts` pour la leçon 14 (métadonnées inchangées).

### 3.2 Nouvelle leçon `lesson-15-choosing-emission.tsx`

Format identique aux leçons existantes (TSX + Tailwind, sections `<h2>` puis `<p>`,
`FurtherReading` final, optionnel `presetTopologyYaml` dans les métadonnées).

**Métadonnées dans `lessons/index.ts`** :
```ts
{
  id: "lesson-15-choosing-emission",
  category: "selection",
  order: 4,                       // après 13 (features, order=2) et 14 (comparing, order=3)
  title: "Choosing the emission distribution",
  estimatedMinutes: 12,
  difficulty: "Intermediate",
  description:
    "Your transitions are fine, your features are clean, yet held-out log-likelihood collapses. The culprit is often the emission. A diagnostic recipe, what to do inside hmm-studio, and what's beyond.",
  status: "published",
  content: Lesson15ChoosingEmission,
  presetTopologyYaml: <preset GMM-HMM 3 états × 3 composantes, 2 features>,
}
```
Plus l'import correspondant en tête de `index.ts`.

**Plan des sections du composant `Lesson15ChoosingEmission`** :

1. **Symptoms of a wrong emission** (paragraphe) — held-out log-likelihood qui
   s'effondre avec une variance énorme entre folds CV ; résidus par état qui ne
   ressemblent pas à la famille d'émission supposée (e.g. queues lourdes contre une
   gaussienne à variance fixe).

2. **Diagnostic recipe** (paragraphe + 3 puces) — (i) fit, (ii) décoder en états
   (Viterbi ou posterior), (iii) tracer l'histogramme des résidus par état contre la
   densité de l'émission. Si l'écart visuel est flagrant ou si l'écart-type de la
   LL/obs hold-out est >> sa moyenne, l'émission est probablement le problème.

3. **The remedy inside hmm-studio: GMM-HMM** (paragraphe + lien interne) — quand
   « one Gaussian per state isn't enough », un GMM avec quelques composantes par état
   peut mimer queues lourdes et multi-modes. Lien vers la leçon 8 et le preset YAML
   ci-dessus. Caveat : ce n'est pas une vraie loi à queue lourde, juste une
   approximation par mélange.

4. **Beyond GMM** (paragraphe + 3-4 puces sourcées) — un panorama bref des options de
   recherche pour aller plus loin que GMM, **avec verdict honnête** :
   - **Multivariate skew-T mixture** (Lee & McLachlan 2011, EMMIXuskew/EMMIXcskew) :
     extension la plus *low-risk* depuis Student-T. EM exact (pas de Monte Carlo),
     gère queues lourdes ET asymétrie. **Recommandation #1**.
   - **Generalized Hyperbolic (GH) HMM** (Foroni, Merlo & Petrella, arXiv:2412.03668,
     déc. 2024) : nest Student-T, NIG, VG ; publié spécifiquement pour les rendements
     financiers multivariés. EM pénalisé avec L1 sur les précisions. **Recommandation
     #2** (strict generalization de Student-T).
   - **Normalizing flows comme émission** (FlowHMM NeurIPS 2022, NMM-HMM,
     arXiv:2102.07284) : architecturalement viable, EM + SGD hybride, implémentations
     publiques. Mais aucune preuve revue par pairs qu'ils battent Student-T sur la
     log-vraisemblance hold-out financière à n≈3500, et les estimateurs neuronaux
     surapprennent sévèrement dans ce régime (Rothfuss et al., ICLR 2020). À différer.
   - **Bases de Fourier / fonction caractéristique** : ne ressort dans aucune source
     primaire comme famille d'émission HMM. **Pas une route à pousser** — préférer
     skew-T mixture ou GH.

5. **Case study (corrected)** (encart) — résumé du re-benchmark A sur ETH : Gaussian
   s'effondre (LL/obs ≈ −200 à −400), Student-T tient (≈ −6.3), Skew-T sous-performe
   Student-T, NHMM n'apporte rien vs Student-T homogène. Pointeur vers la table
   corrigée dans `Projet_Robin/README.md` et la spec
   `2026-05-27-model-rebenchmark-design.md`.

6. **Try it** (paragraphe + bouton) — preset YAML GMM-HMM à 3 états × 3 composantes
   sur features 2D, à charger dans l'éditeur depuis la carte de la leçon.

7. **FurtherReading** (composant existant) — les 4 références bibliographiques de la
   section « Beyond GMM » (Lee & McLachlan, Foroni-Merlo-Petrella, FlowHMM,
   Rothfuss et al.), plus un pointeur vers la spec A et la leçon 14.

### 3.3 Tests / vérifications

- Compilation TypeScript / build Vite doit passer sans erreur sur les deux fichiers
  (le seul vrai contrat est que le composant s'exporte avec la bonne signature et que
  `index.ts` typecheck après ajout).
- Si la suite de tests frontend existante a un test « toutes les leçons publiées
  exposent un `content` callable et un `id` unique », la leçon 15 doit y passer
  automatiquement par construction. À vérifier au début de l'implémentation, pas à
  inventer si rien n'existe.
- Aucun test backend (les leçons sont du contenu frontend statique).

### 3.4 Alternatives considérées

- **Refactoriser la leçon 14 en 14a/14b (split)** : rejeté, sur-ingénierie pour une
  mise à jour ciblée de trois paragraphes.
- **Construire un composant interactif (« diagnostic playground »)** pour la leçon 15 :
  rejeté pour ce scope. Les composants interactifs existants (MarkovChainDemo,
  NhmmBreathing, Trellis) sont chacun un design substantiel à part entière. Hors
  scope ; à proposer comme sous-projet séparé si la leçon est bien reçue.
- **Ajouter Student-T comme émission native dans hmm_studio** : c'est essentiellement
  le sous-projet D-bis, hors scope ici. La leçon 15 le présente comme « beyond » et
  pointe vers la recherche.

## 4. Scope boundaries

- **Out** : ajout de Student-T / skew-T / GH / flows comme émission native dans
  hmm_studio. C'est un sous-projet d'ampleur (nouveau backend ou extension hmmlearn).
- **Out** : nouveau composant React interactif pour la leçon 15.
- **Out** : changement des catégories existantes ou réorganisation de l'index.
- **Out** : modifications à la leçon 8 (GMM-HMM) ou à toute autre leçon.

## 5. Open questions (défauts retenus — à confirmer à la relecture)

1. **Preset YAML de la leçon 15** : *défaut retenu* — GMM-HMM, 3 états, 3 composantes
   par état, 2 features, covariance `full`, init kmeans, 50 itérations Baum-Welch.
   Petits chiffres pour rester lisible dans l'éditeur. À confirmer.
2. **Pointeur vers Projet_Robin depuis hmm_studio** : *défaut retenu* — lien
   *texte* (chemin relatif `../Experiment.Crypto.2026S1.NathanBerbinau/Projet_Robin/...`)
   plutôt qu'URL externe, puisque les deux projets cohabitent sous le même workspace.
   Si hmm_studio est publié séparément (npm/site), il faudra une URL GitHub publique
   à terme — pas bloquant pour la leçon.
3. **Inclure l'option « Fourier » dans la leçon 15** : *défaut retenu* — oui, en une
   ligne, pour clore explicitement la question (« no primary source as an HMM emission
   family — prefer skew-T mixture or GH »). Évite que le sujet revienne plus tard.

## Update 2026-05-28 — bullet Fourier retiré de la leçon 15

Après écriture, retour utilisateur sur un cadrage pédagogique : **le GMM lui-même est
une décomposition par fonctions de base**, conceptuellement parente d'une décomposition
de Fourier (somme pondérée de noyaux gaussiens vs somme pondérée de sinusoïdes, avec la
propriété d'approximateur universel des densités). Le bullet original « Fourier-basis /
characteristic-function HMM emissions — no primary source » devenait alors trompeur :
un lecteur pouvait conclure « les approches Fourier-like ne marchent pas » alors que
GMM **est** une approche Fourier-like (et marche).

Le bullet a été retiré. La distinction préservée : ma deep-research portait sur des
émissions HMM littéralement paramétrées par une **base sinusoïdale** ou par leur
**fonction caractéristique** — pour lesquelles aucune source primaire ne ressort. Cette
question reste sans support empirique, mais ne mérite pas d'apparaître dans la leçon
parce qu'elle prête à confusion avec le cadrage GMM-comme-base-de-fonctions.

Les 3 bullets restants de « Beyond GMM » sont inchangés (skew-T mixture #1, GH #2,
normalizing flows à différer). Les 4 références dans `FurtherReading` et dans
`academy-references.md` restent toutes pertinentes pour ces 3 bullets.
