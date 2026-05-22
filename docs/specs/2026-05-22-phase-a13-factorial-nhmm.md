# Phase A.13 — Factorial NHMM : spec

**Date** : 2026-05-22
**Auteur** : Robin Denis (avec architecte-CEO framing)
**Status** : ✅ **SHIPPED 2026-05-22 — Strategy A (2-stage decomposition)** + V.6 cross-check
**Effort réel** : ~1 jour (Strategy A bénéficie de A.1 + A.5 + leçon A.10)
**Prérequis durs** : A.1 (NHMM ✓), A.5 (backend abstraction ✓), V (validation suite ✓), A.10 (GMM-NHMM — pattern 2-stage validé ✓)

> **Découverte d'implémentation 2026-05-22 PM (continuité directe de la
> leçon A.10)** : la rédaction initiale du spec proposait Strategy A
> comme "joint state expansion ∏K_d states avec mask factorisé". Cette
> approche s'est révélée **incorrecte** pour la même raison qu'A.10 : la
> NHMM logit sur ∏K_d outcomes par état source aurait
> $(∏K_d)^2 \cdot P$ coefficients libres SANS contrainte de
> factorisation $\prod_d A^{(d)}_{i_d j_d}$. Le modèle obtenu serait
> sur-paramétré.
>
> La **Strategy A livrée** est **2-stage decomposition** :
>   1. Stage 1 : Gaussian HMM ergodic sur $K_{joint} = \prod_d K_d$ états
>      avec l'émission jointe → donne μ et Σ par tuple + Viterbi joint
>   2. Stage 2 : projeter Viterbi joint → per-chain trajectories via
>      `np.unravel_index` → fit NHMM logit indépendant par chaîne avec
>      ses propres covariates
>
> **Économie de paramètres documentée par V.6.4** : pour D=3, K_d=3 :
> $(\prod K_d)^2 \cdot P = 729P$ → $\sum_d K_d^2 \cdot P = 27P$. **27×
> moins de coefficients libres**, dramatiquement plus identifiable sur
> petites données.
>
> Module : `src/hmm_core/factorial_nhmm.py`. Public API :
> `fit_factorial_nhmm()` + `FactorialNHMMFittedModel`. 14 tests + 5 V.6
> cross-checks tous verts.

> Document de spec. Pour le contexte stratégique, voir
> [docs/roadmap.md § Phase A.13](../roadmap.md).

---

## 1. Contexte et motivation

### Le besoin moteur (crypto multi-facteur)

Les régimes du marché crypto ont **plusieurs dimensions qui évoluent
indépendamment** :

1. **Trend regime** ∈ {bear, range, bull} — orientation directionnelle
2. **Volatility regime** ∈ {low-vol, normal, high-vol} — niveau d'agitation
3. **Macro regime** ∈ {risk-on, risk-off} — contexte cross-asset

Modéliser ces 3 dimensions comme un seul HMM à 3×3×2 = **18 états** force
des **transitions synchrones** : toutes les dimensions changent
simultanément ou aucune ne change. C'est **faux empiriquement** :
- La vol peut spiker (low → high) sans que le trend change
- Le macro peut basculer (risk-on → risk-off) avant que le trend ne réagisse
- Les transitions des 3 dimensions ont leurs propres temporalités

**Factorial HMM** modélise D chaînes de Markov **indépendantes** générant
conjointement les observations. Chaque chaîne :
- a sa propre matrice de transition
- a ses propres covariates (en version NHMM)
- évolue indépendamment des autres

C'est exactement le bon modèle pour le cas crypto.

### Précédent et état de l'art

- **Ghahramani & Jordan 1997** — "Factorial Hidden Markov Models",
  Machine Learning 29:245-273. **L'article fondateur**, formulation
  exacte + variationnelle structurée.
- Implémentations Python : aucune complète au 2026-05-22. Quelques
  tentatives sur GitHub mais soit incomplètes, soit non-maintenues.
- En finance : "Multi-regime Markov-switching" est utilisé en
  économétrie mais souvent avec 2 régimes seulement et états joints.

**Notre opportunité** : être la première implémentation Python complète et
maintenue de **Factorial NHMM**, ciblant le wedge finance/quant +
recherche.

### Pourquoi c'est on-strategy

1. **Cas d'usage direct Robin** (crypto) — pas de gating signal externe
2. **Renforce le wedge "interpretability-mandate" finance** — les quants
   adorent les modèles décomposables
3. **Étend l'architecture A.5** — encore un backend non-hmmlearn, validant
   le découplage
4. **Combine naturellement avec A.10 (GMM-NHMM)** dans le futur (A.13.1)
   — pas dans le MVP

## 2. Formulation mathématique

### Modèle Factorial NHMM

- D chaînes de Markov : $z^{(d)}_t \in \{1, \dots, K_d\}$ pour $d \in [D]$
- Transitions covariate-dependent par chaîne (NHMM standard) :
  $$A^{(d)}_{ij}(u^{(d)}_t) = \frac{\exp(\beta^{(d)}_{ij}{}^\top u^{(d)}_t)}{\sum_{j'} \exp(\beta^{(d)}_{ij'}{}^\top u^{(d)}_t)}$$
- État initial : $\pi^{(d)}_k$ par chaîne (indépendantes)
- Émission **jointe** : observation $x_t$ générée à partir des D états
  $z^{(1)}_t, \dots, z^{(D)}_t$ simultanément

### Choix du modèle d'émission

Deux paramétrisations classiques pour l'émission jointe :

#### Option A : Émission paramétrée par le tuple
$$p(x_t \mid z^{(1)}_t = k_1, \dots, z^{(D)}_t = k_D) = \mathcal{N}(x_t \mid \mu_{k_1, \dots, k_D}, \Sigma_{k_1, \dots, k_D})$$

Chaque combinaison $(k_1, \dots, k_D)$ a ses propres $(\mu, \Sigma)$.
Nombre de paramètres : $\prod_d K_d$ moyennes + covariances.

**Avantages** : expressivité maximale ; capture interactions
non-linéaires entre dimensions.
**Inconvénients** : explosion combinatoire des paramètres.

#### Option B : Émission additive (Ghahramani-Jordan classique)
$$p(x_t \mid z^{(1)}_t, \dots, z^{(D)}_t) = \mathcal{N}\left(x_t \;\Big|\; \sum_{d=1}^D \mu^{(d)}_{z^{(d)}_t}, \; \Sigma\right)$$

Effet de chaque chaîne sur la moyenne est **additif**. Une seule covariance
partagée.

**Avantages** : nombre de paramètres en $\sum_d K_d$, pas $\prod_d K_d$ ;
interprétation facile ("contribution de la chaîne d").
**Inconvénients** : suppose pas d'interactions entre dimensions ; peut être
trop restrictif pour crypto (où trend × vol peut avoir effet
multiplicatif).

### Notre choix : Option A en MVP, Option B en optionnel

- Option A est plus expressive et plus fidèle au cas crypto
- $\prod_d K_d$ paramètres est gérable tant que $\prod_d K_d \leq 27$
  (D=3 avec K_d=3 max)
- Option B sera ajoutée comme `emission.factorial_kind: "additive"` plus tard

### Likelihood et inférence

**Complete data likelihood** (D + 1 niveaux de latence : D chaînes) :
$$p(z^{(1:D)}, x \mid u^{(1:D)}) = \prod_{d=1}^D \pi^{(d)}_{z^{(d)}_1} \prod_{t=2}^T A^{(d)}_{z^{(d)}_{t-1}, z^{(d)}_t}(u^{(d)}_t) \cdot \prod_{t=1}^T p(x_t \mid z^{(1:D)}_t)$$

**Forward-backward exact** : opère sur l'espace joint $\prod_d K_d$ états.
Complexité $O(T \cdot (\prod_d K_d)^2)$. Pour D=3, K_d=3 → $27^2 = 729$
multiplications par pas, $T \cdot 729$ au total. Fine pour T jusqu'à
~100000 (sur des CPUs modernes en numpy vectorisé).

**Forward-backward variationnel structuré** (Ghahramani-Jordan 1997) :
approximer la postérieure jointe par un produit de postérieures par chaîne :
$$q(z^{(1:D)} \mid x) = \prod_{d=1}^D q^{(d)}(z^{(d)} \mid x)$$
Mise à jour itérative : chaque $q^{(d)}$ est calculé en supposant les autres
$z^{(d')}$ fixés à leur expectation courante. Complexité $O(T \sum_d K_d^2)$
au lieu de $O(T \prod_d K_d^2)$. Crucial pour D ≥ 4 ou K_d ≥ 5.

## 3. Stratégies d'implémentation (C hybride, comme A.10)

### Stratégie A — Joint state expansion (MVP)

**Principe** : encoder le Factorial HMM comme un HMM à $\prod_d K_d$ états
avec **matrice de transition factorisée** :

$$A_{(i_1, \dots, i_D), (j_1, \dots, j_D)}(u_t) = \prod_{d=1}^D A^{(d)}_{i_d, j_d}(u^{(d)}_t)$$

C'est une **contrainte structurelle forte** sur une matrice $\prod K_d \times \prod K_d$ qu'on peut encoder via :
- Notre `Topology` étendue avec `type='factorial'` + `chains: [topo1, topo2, ...]`
- Un mask block qui force la factorisation

**Avantages** : réutilise A.1 NHMM + A.5 backend + A.10 patterns
intégralement. **3-5 jours** d'effort.

**Inconvénients** :
- Limite $\prod_d K_d \leq 27$ (au-delà : Strategy B obligatoire)
- Le BIC nominal compte les params du modèle équivalent étendu (à corriger
  manuellement avec compte vrai des params Factorial)
- Decoding Viterbi retourne tuples $(k_1, \dots, k_D)$ qu'il faut projeter

### Stratégie B — Direct Factorial NHMM via variational inference

**Principe** : implémenter `NumpyFactorialNHMMBackend` avec :
- Représentation native de D chaînes
- Forward-backward variationnel mean-field structuré (Ghahramani-Jordan)
- M-step par chaîne (régression logistique pondérée pour transitions
  covariate-dependent, identique à A.1 NHMM)
- M-step émission joint

**Avantages** :
- Scale à grand D et grand K_d
- Decoding natif par chaîne
- BIC correct
- Permet vraiment de combler le trou Python

**Inconvénients** :
- ~1-1.5 semaine d'effort additionnel
- Inférence variationnelle = approximation (la borne ELBO n'est pas la
  vraie log-likelihood) → besoin de cross-check vs Strategy A sur petits cas

### Stratégie C — Hybride (recommandée, cohérent avec A.10)

1. **MVP** : Strategy A (joint state expansion) — 3-5 jours
2. **Validation V.6** : Strategy B comme oracle indépendant — vérifie que
   Strategy A et B donnent ELBO ≈ log-likelihood vraie sur jouets canoniques
3. **Si V.6 passe** : Strategy A reste impl primaire, Strategy B disponible
   pour cas $\prod K_d > 27$
4. **Si V.6 révèle une limite** : Strategy B devient primaire

## 4. API publique

### YAML topology étendue

```yaml
name: btc_3_factor_regimes
type: factorial                       # ← nouveau type top-level
chains:
  - name: trend
    n_states: 3
    state_names: [bear, range, bull]
    transitions:
      type: covariate
      covariates: [momentum_20, momentum_60]
  - name: volatility
    n_states: 3
    state_names: [low_vol, normal, high_vol]
    transitions:
      type: covariate
      covariates: [realized_vol_5, realized_vol_20]
  - name: macro
    n_states: 2
    state_names: [risk_on, risk_off]
    transitions:
      type: covariate
      covariates: [vix_z, dxy_z]
emission:
  type: gaussian                      # joint emission paramétré par tuple
  covariance_type: full
  n_features: 1                       # log_return
  factorial_kind: tuple               # "tuple" (Option A) ou "additive" (Option B)
startprob: uniform_per_chain
init:
  strategy: kmeans_joint
  seed: 42
fit:
  algorithm: baum_welch_factorial
  n_iter: 200
  inference: exact                    # "exact" (Strategy A) ou "variational" (Strategy B)
  regularization: 0.01
```

### Python API

```python
from hmm_core.fit import fit
from hmm_core.io import load_topology
import pandas as pd
import numpy as np

topo = load_topology("btc_factorial.yaml")
X = pd.read_csv("btc_returns.csv").to_numpy()
covariates_per_chain = {
    "trend":      pd.read_csv("trend_covariates.csv").to_numpy(),
    "volatility": pd.read_csv("vol_covariates.csv").to_numpy(),
    "macro":      pd.read_csv("macro_covariates.csv").to_numpy(),
}

result = fit(topo, X, covariates=covariates_per_chain)

# Accès aux résultats par chaîne
print(result.model.chains["trend"].transmat_)        # (3, 3) — moyenne
print(result.model.chains["volatility"].emission_contribution)  # si additive
print(result.model.emissions)                        # joint emissions param

# Décodage indépendant par chaîne (Strategy A : décoder joint puis projeter)
backend = get_backend()
trend_path = backend.decode_chain(result.model, X, chain="trend")
vol_path = backend.decode_chain(result.model, X, chain="volatility")
macro_path = backend.decode_chain(result.model, X, chain="macro")

# Décodage joint
joint_path = backend.decode_joint(result.model, X)  # shape (T, D)
```

### CLI extension

```bash
hmm-fit run btc_factorial.yaml btc_returns.csv \
    --covariates-trend trend_features.csv \
    --covariates-volatility vol_features.csv \
    --covariates-macro macro_features.csv \
    --output results/btc_factorial

hmm-fit show results/btc_factorial/model.pkl
# Affiche : D=3 chaînes, K=[3,3,2], log-lik, BIC, transmat par chaîne
```

## 5. Tests

### Tests unitaires (`tests/test_factorial_nhmm.py`)

| Test | Vérifie |
|---|---|
| `test_factorial_topology_validates` | YAML factorial avec D chaînes valide |
| `test_factorial_chains_independent` | Sur données simulées avec chaînes indépendantes, transitions par chaîne récupérées correctement |
| `test_factorial_joint_emission_recovered` | $\mu_{k_1,k_2}$ récupérés sur jouet |
| `test_factorial_decode_joint_returns_DT` | `decode_joint` retourne (T, D) |
| `test_factorial_decode_chain_returns_T` | `decode_chain("trend")` retourne (T,) |
| `test_factorial_BIC_counts_correctly` | BIC compte les vrais params, pas $\prod K_d$ étendu |
| `test_factorial_handles_per_chain_covariates` | Chaque chaîne a ses propres covariates indépendamment |
| `test_factorial_warns_at_K_product_too_large` | Warning explicite si $\prod K_d > 27$ |
| `test_factorial_strategy_A_consistent` | Strategy A équivalente à un HMM joint $\prod K_d$ états avec mask factorisé |
| `test_factorial_label_switching_per_chain` | Multi-start retourne params permutationally équivalents par chaîne |

### Tests Phase V.6 (validation cross-check)

| Test | Vérifie |
|---|---|
| `test_v6_strategy_A_equiv_strategy_B_D2_K2` | Strategy A (exact) vs B (variational) log-lik écart < 5 % sur D=2 K=2 |
| `test_v6_strategy_A_equiv_strategy_B_D2_K3` | Idem D=2 K=3 |
| `test_v6_decoding_consistency_A_B` | Viterbi par chaîne match à ≥ 95 % |
| `test_v6_BIC_consistency_A_B` | BIC écart < 5 % |

## 6. Limites d'identifiabilité

Factorial est riche, sur-paramétrable, vulnérable au label switching.

### Limites recommandées (warnings)

- **$D \leq 3$** dans MVP Strategy A (au-delà : Strategy B)
- **$K_d \leq 3$** par chaîne dans MVP
- **$\prod_d K_d \leq 27$** (constraint dur en Strategy A)
- **$P_d \leq 6$** covariates par chaîne
- **$T \geq 300 \cdot$ free_params** (factorial encore plus glouton que NHMM)

### Régularisations

- L2 sur $\beta^{(d)}_{ij}$ par chaîne (default 0.01)
- Floor sur covariance jointe : $\Sigma \mathrel{+}= 10^{-3} I$
- Symmetry breaking init : décaler les init par chaîne pour éviter
  l'effondrement initial (e.g. toutes les chaînes identifient le même
  régime)

### Identifying constraints

- Au sein d'une chaîne d, ordonner les états par $\mu^{(d)}_{k,1}$ (effet
  marginal additif si Option B, marginal empirique si Option A)
- Entre chaînes, **pas de permutation** : la nomination des chaînes est
  fixée par l'utilisateur (trend, volatility, macro)

## 7. Intégration dashboard crypto (Phase D)

Test produit ultime, identique au pattern A.10 :

1. Adapter le YAML crypto pour exposer 3 chaînes : trend, volatility, macro
2. Fitter Factorial-NHMM(3 chaînes) vs NHMM unique 18-état (3×3×2)
3. Comparer :
   - log-likelihood
   - BIC, AIC
   - Visualisation des trajectoires par chaîne (heatmap individuelle)
   - **Interprétation domaine** : Robin vérifie manuellement que les
     trajectoires de chaque chaîne ont du sens
4. Si gain significatif (BIC factorial < BIC unique 18-état) → A.13 validé
   en production
5. Si pas de gain → documenter explicitement, A.13 reste utile pour le
   wedge interpretability (séparation des dimensions de régime)

## 8. Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Convergence EM lente (D niveaux de latence) | Élevée | Multi-start (15-20 init), max_iter=500, monitoring tight de log-lik |
| Identifiabilité fragile entre chaînes | Élevée | Init par chaîne décalée + identifying constraints strictes |
| Strategy A et B divergent significativement | Moyenne | V.6 cross-check obligatoire avant ship ; flag si écart > 5 % |
| $\prod K_d$ explose pour grand D | Élevée si user fait n'importe quoi | Warning + hard limit à 27 ; pointer vers Strategy B variational |
| BIC trompeur (Strategy A compte mauvais params) | Élevée | Calcul BIC explicite Factorial dans le code, pas via HMM joint |
| Émission paramétrée par tuple sur-fit avec little data | Élevée | Régularisation forte sur $\mu_{k_1..k_D}$ ; recommander Option B (additive) si T < 1000 |
| Pas de gain BIC vs HMM unique 18-état sur crypto réel | Faible-Moyenne | Documenter l'absence de gain ; A.13 reste utile pour interprétabilité |
| Confusion utilisateur entre "factorial" et "hierarchical" | Moyenne | Documentation extensive + Academy lesson dédiée + table comparative variants HMM |

## 9. Définition de "done"

- [ ] `type: factorial` accepté dans Topology + validation YAML
- [ ] Strategy A (joint state expansion) implémentée dans dispatcher
- [ ] Strategy B (`NumpyFactorialNHMMBackend`) implémentée comme backend optionnel
- [ ] 10 tests unitaires dans `tests/test_factorial_nhmm.py`
- [ ] 4 tests V.6 dans `validation/test_v6_factorial.py`
- [ ] Section README "Factorial NHMM for multi-factor regimes"
- [ ] Notebook example `examples/btc_factorial_nhmm.ipynb` (optionnel)
- [ ] ADR-0009 sur le choix Strategy C hybride pour factorial
- [ ] Validation produit sur dashboard crypto : gain BIC documenté ou
      absence de gain documentée + visualisation des trajectoires par
      chaîne (signal qualitatif fort)

## 10. Successeurs hors-scope (anti-scope-creep)

- **A.13.1** : Factorial GMM-NHMM (combine A.10 + A.13) — c'est tentant
  mais $\prod K_d \cdot \prod M_d$ explose. Reportée tant que Robin n'en a
  pas besoin.
- **A.13.2** : Factorial-NHMM avec chaînes **couplées** (sortie de chaîne d
  comme covariate d'une autre) — bridge vers Coupled HMM. Reject sauf
  signal explicite, ou laisser comme cas d'usage NHMM standard.
- **A.13.3** : Factorial Hierarchical (cross avec A.11) — recherche
  exotique. Reject.
- **A.13.4** : Inférence Bayesian variationnelle complète (variational
  inference + priors) — intersection avec A.6 (gated). Defer.

## 11. ADR à créer

`docs/decisions/0009-factorial-nhmm-strategy-c.md` :
- Pourquoi Factorial est-il promu (vs reject initial) ?
- Pourquoi Strategy C hybride ?
- Pourquoi Option A (tuple emission) en MVP plutôt qu'Option B (additive) ?
- Limites identifiabilité posées et justification

## 12. Références scientifiques

- **Ghahramani & Jordan 1997** — "Factorial Hidden Markov Models",
  Machine Learning 29:245-273. Article fondateur, formulation exacte +
  variationnelle structurée. À implémenter contre.
- **Murphy 2012** — "Machine Learning: A Probabilistic Perspective",
  chapitre 17. Synthèse moderne, cadre dynamic Bayesian network.
- **Saul & Jordan 1999** — "Mixed Memory Markov Models : Decomposing
  Complex Stochastic Processes as Mixtures of Simpler Ones", Machine
  Learning 37:75-87. Variante intéressante à connaître.
- **Diebold, Lee & Weinbach 1994** — TVTP en Markov-switching. Applicable
  par chaîne dans notre formulation NHMM.
- Notre propre A.1 NHMM, A.5 backend abstraction, A.10 GMM-NHMM pour le
  pattern.
