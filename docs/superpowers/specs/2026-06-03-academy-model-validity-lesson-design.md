---
Status: current
---

# Academy — Leçon 16 « When is your model valid? (and when NOT to use an HMM) »

*Spec écrit le 2026-06-03. Retour utilisateur : « Faire une leçon : when is your
model valid / criteria ? Est-ce que c'est déjà expliqué dans Academy ? » + décision :
« quand NE PAS utiliser un HMM » est **fondu dans** cette leçon de validité.*

## 1. Contexte / problème

L'Academy hmm-studio compte **15 leçons** (`lesson-1` … `lesson-15`,
`src/hmm_studio/frontend/src/lessons/`). Plusieurs touchent à la validité **par axe**,
mais **aucune ne donne le cadre unifié « mon modèle est-il valide ? »** :

- **L.5 Baum-Welch** — convergence + optima locaux (angle *algorithme*, pas *diagnostic*).
- **L.6 Topologies contraintes** — choisir la bonne structure (suppose la topologie donnée).
- **L.13 Choosing features** — décorréler les features (sélection, pas validation a posteriori).
- **L.14 Comparing models** — comparer des modèles **différents** par BIC/AIC/HQIC.
- **L.15 Choosing emission** — symptômes d'une **émission** mal choisie (un axe de validité).

Le trou : il manque la leçon qui **(a)** énonce les **hypothèses** d'un HMM, **(b)**
donne une **checklist de diagnostic** d'un modèle *unique* (avant / pendant / après le
fit), **(c)** dit **quand rejeter le HMM** au profit d'un autre outil. Le projet avait
par ailleurs une intention roadmap « Quand NE PAS utiliser un HMM » (leçon
d'honnêteté intellectuelle) — l'utilisateur a tranché : **on la fond ici**, pas de
leçon séparée trop mince.

hmm-studio a déjà **toutes les briques** pour ancrer cette leçon dans ses propres
outils (et non en théorie générique) : critères d'info, comparaison de modèles,
décodage Viterbi/postérieurs, labelling de régimes, écrans web de fit/compare. C'est
le différenciateur (comme L.14/L.15 qui enseignent avec les outils maison).

## 2. Objectif

Une leçon Academy **`lesson-16-model-validity`** (Advanced, ~15-18 min, catégorie
`selection`, ordre 5 après L.15) qui donne au lecteur un **cadre opérationnel de
validité** : les 5 hypothèses, une checklist avant/pendant/après fit **branchée sur
les vrais primitives hmm-studio**, et des critères go/no-go pour **renoncer au HMM**.
Succès = un utilisateur sait répondre, preuves à l'appui, à « ce HMM est-il
crédible ? » et « est-ce seulement le bon outil ici ? » — en utilisant `FittedModel`,
`compare_models`, le décodage et les écrans web existants, **sans nouveau backend**.

## 3. Design

### 3.1 Cadre pédagogique (le plan de la leçon)

Sections (style maison : `h2` + listes + blocs code + composants + `FurtherReading`) :

1. **Why this matters** — un cas d'échec (held-out LL catastrophique : topologie ?
   features ? émission ? init ?) qui motive un *cadre* plutôt qu'un réflexe.
2. **Les 5 hypothèses** — stationnarité (transitions/émissions stables dans le temps),
   propriété de Markov (dépendance lag-1), indépendance conditionnelle des émissions
   sachant l'état, espace d'états fini & K (à peu près) connu, **identifiabilité**
   (paramètres stables across inits/seeds). Cite L.1 (hypothèses) + L.7 NHMM (non-stationnarité).
3. **Vérifier *avant* le fit** — stationnarité/regime-shift, autocorrélation au-delà du
   lag 1 (ACF → viole Markov), features prédictives du régime (renvoi L.13), K plausible.
4. **Surveiller *pendant* le fit** — `converged`, LL monotone qui plafonne, **multi-init**
   (top-3 LL divergents = optimum local), stabilité des paramètres entre seeds,
   label-switching. *Ancrage* : `FittedModel.converged` / `n_iter_actual`, l'écran de
   fit **WebSocket** live (`/ws/fit/{id}`), `fit_log.txt`, et le composant existant
   **`BaumWelchAnimation`** (réutilisé de L.5) pour la courbe de convergence.
5. **Diagnostiquer *après* le fit** — Viterbi (`predict`) + postérieurs (`predict_proba`,
   entropie aux transitions), durées de séjour par état, occupations ~0 (sur-fragmentation),
   résidus par état vs densité ajustée (renvoi L.15), `mask_violation_norm < 1e-10`,
   interprétabilité des transitions, labelling `regimes.regime_labels` + stabilité de
   l'ordre des états across seeds.
6. **Quand renoncer au HMM** (la moitié « honnêteté ») — données non-stationnaires à
   régimes mouvants → NHMM/switching, pas HMM vanilla ; dépendance longue portée (ACF
   à lags > ~5) → AR/state-space ; trop peu d'obs/paramètre → priors bayésiens (L.10) ;
   régimes non séparables en feature-space → réduction de dim / fusion d'états ; K
   inconnu sans guidage → commencer K=2, valider par CV/bootstrap, ne pas grid-search
   sans validation. *Source honnête* : positionnement roadmap (Transformers/SSM
   dominent le gros data / NLP / longues séquences ; niches où le HMM gagne =
   petit data, états discrets interprétables, audit/réglementaire, enseignement).
7. **Un workflow de diagnostic** — recette en 6-7 étapes : multi-init → `compare_models`
   / `auto_grid` (BIC) → décoder & inspecter durées/moyennes → résidus → held-out LL →
   labelling stable → verdict provisoire. *Ancrage* : `compare_models(X, candidates)`,
   `auto_grid(...)`, `HMMClassifier.score` + **TimeSeriesSplit** (pas KFold aléatoire).
8. **Try it** — pointer l'écran **`/compare`** (table classée par critère) + un preset
   chargeable dans l'éditeur de topologie.
9. **See also** — `Link` vers L.1 / L.5 / L.6 / L.13 / L.14 / L.15.
10. **Further reading** — Bilmes 1998 (EM), Celeux & Soromenho 1996 (label-switching),
    Murphy MLAPP §16, + renvoi à la **Phase V** (V.1-V.4) comme « voici comment *nous*
    validons hmm-studio » (cross-check hmmlearn, recovery synthétique, problèmes textbook,
    stabilité numérique).

### 3.2 Décisions de design (et alternatives écartées)

- **Ancrée aux outils maison, pas théorie générique.** *Alternative* : leçon prose
  théorique. *Écartée* : le différenciateur Academy est d'enseigner avec les diagnostics
  hmm-studio réels (cohérent L.14/L.15). Chaque check cite une primitive existante.
- **« Quand NE PAS utiliser » fondu en section 6** (décision utilisateur). *Alternative* :
  leçon séparée. *Écartée* : trop mince seule ; c'est le pendant naturel de la validité
  (« le modèle est-il valide ? » inclut « est-ce le bon modèle ? »). Supersede l'item
  roadmap « leçon honnêteté » distinct.
- **Réutiliser `BaumWelchAnimation` + écran fit live, PAS de nouveau widget en v1.**
  *Alternative* : composant `ConvergenceDiagnostics` custom (courbe LL d'un modèle figé,
  détecteur de label-switching, heatmap de stabilité). *Écartée pour v1* : la **trace LL
  par itération n'est ni sur `FittedModel` ni exposée par l'API REST** (seulement
  `fit_log.txt` + WebSocket live) → un tel widget exigerait du **backend**. v1 enseigne
  la convergence via le composant L.5 (synthétique) + l'écran WebSocket + une mention de
  `fit_log.txt`. Le widget custom est une amélioration **future, hors-scope** (cf. §5).
- **Quiz obligatoire** (`LESSON_QUIZZES['lesson-16-model-validity']`) : ~4 flashcards
  (5 hypothèses, optima locaux, label-switching) + 5-6 questions Apply/Analyze de type
  « symptôme X → cause/action Y » (états confondus & transitions aléatoires →
  non-identifiable ; held-out LL ≫ train → overfit/émission ; ACF lags 5-20 → viole Markov).
- **Backlinks réciproques minimaux** : ajouter un « See also → L.16 » dans **L.14** et
  **L.15** (règle de maintenance des leçons ; édition d'1-2 lignes chacune).

### 3.3 Intégration technique (fichiers touchés)

- **Nouveau** `src/hmm_studio/frontend/src/lessons/lesson-16-model-validity.tsx`
  (export `Lesson16ModelValidity`).
- **`lessons/index.ts`** — import + entrée `LESSONS` : `{ id:'lesson-16-model-validity',
  category:'selection', order:5, difficulty:'Advanced', estimatedMinutes:16,
  status:'published', title:"When is your model valid? (and when NOT to use an HMM)",
  description:…, content: Lesson16ModelValidity }`. Optionnel `presetTopologyYaml`.
- **`components/academy/lessonQuiz.ts`** — entrée `LESSON_QUIZZES`.
- **`lesson-14`/`lesson-15`** — un backlink « See also » chacun.
- **Aucun changement backend / API.** Réutilise `BaumWelchAnimation`, `FurtherReading`,
  `Link`. Test : suivre le tier existant (les leçons n'ont pas de test unitaire dédié ;
  un smoke e2e Academy `e2e/tests/academy.spec.ts` peut asserter que la leçon route +
  rend + le quiz s'ouvre).

## 4. Bornes de scope

- **IN** : la leçon-16 (.tsx) + enregistrement index + quiz + 2 backlinks. Ancrée aux
  **API existantes uniquement**.
- **OUT** : tout backend nouveau — **pas** de `FittedModel.convergence_history`, pas de
  helper CV intégré (TimeSeriesSplit reste un import sklearn côté user), pas de tests
  goodness-of-fit (Ljung-Box…), pas de détecteur automatique de label-switching, pas
  d'exposition REST de la trace LL. Pas de **widget interactif lourd** custom (v1). Pas
  de notebook compagnon (optionnel plus tard). Pas de refonte des leçons existantes
  (seulement les 2 backlinks).

## 5. Questions ouvertes

1. **Réconciliation roadmap** : confirmer que la leçon « Quand NE PAS utiliser un HMM »
   planifiée est **consolidée** ici (l'utilisateur a déjà dit oui) → mettre à jour le
   roadmap en conséquence au ship.
2. **Mini-enhancement backend optionnel** : persister `convergence_history` sur
   `FittedModel` + l'exposer sur le résultat de fit permettrait une **vraie courbe de
   convergence** depuis un modèle figé (et un futur widget). *Reco* : **non en v1** —
   ticket séparé ; la leçon marche sans (BaumWelchAnimation + WebSocket + `fit_log.txt`).
3. **Preset « diagnostique-moi »** : forge-t-on un petit preset volontairement
   mal-spécifié (ex. K trop grand → état à occupation ~0) comme accroche hands-on, ou
   réutilise-t-on un preset existant (L.5/L.14) ? *Reco* : un petit preset dédié = bonne
   accroche, faible coût.
4. **Profondeur du quiz** : 4 flashcards + 5-6 questions confirmé ?

## 6. Pointeurs (ancrage code — vérifiés 2026-06-03)

- `FittedModel` : `src/hmm_core/fit/__init__.py:22-34` (log_likelihood, bic, aic, hqic,
  n_iter_actual, converged, seed, duration_seconds) ; formules IC `:284-295` ;
  `mask_violation_norm` `:135-140`.
- Sélection : `src/hmm_core/selection.py:70-251` (`compare_models`/`ModelComparison`),
  `:257-294` (`auto_grid`).
- sklearn-compat : `src/hmm_core/sklearn_compat/classifier.py:30-236` (`.score`,
  docstring TimeSeriesSplit).
- Décodage : `src/hmm_core/backends/_protocol.py:149-157` (`predict`/`predict_proba`).
- Régimes : `src/hmm_core/regimes.py:52-108`. Convergence live :
  `backends/hmmlearn_backend.py:112-151` (progress_callback) ; trace persistée
  `io.py:169-172` (`fit_log.txt`).
- API : `server/app.py` `/api/fit/{id}` (`:211-232`), `/decoded` (`:291-338`),
  `/transmat` (`:262-290`), `/emissions` (`:378-408`), `/ws/fit/{id}` (`:233-260`),
  `/api/fit/compare/*` (`:564-648`).
- Validation projet : `docs/specs/2026-05-22-phase-v-validation.md` (V.1-V.4) +
  `validation/test_v*.py`.
- Conventions Academy : `lessons/index.ts:58-374` (registre, catégories `:19-35`),
  `components/academy/lessonQuiz.ts`, `FurtherReading.tsx`, `BaumWelchAnimation`.
