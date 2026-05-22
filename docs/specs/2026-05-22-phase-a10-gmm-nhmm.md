# Phase A.10 — GMM-NHMM : spec

**Date** : 2026-05-22
**Auteur** : Robin Denis (avec architecte-CEO framing)
**Status** : ✅ **SHIPPED 2026-05-22 — Strategy A (2-stage)** + V.5 cross-check
**Effort réel** : ~1 jour (Strategy A bénéficie massivement de A.1 + A.5)
**Prérequis durs** : A.1 (NHMM livré ✓), A.5 (abstraction backend ✓), V (validation suite livrée ✓)

> **Update post-implémentation 2026-05-22** : Strategy A telle qu'écrite
> initialement (K·M expansion) s'est révélée **mauvaise** car elle aurait
> sur-paramétré le modèle (la NHMM logit sur K·M outcomes n'enforce pas la
> factorisation $A_{ij} \cdot w_{jq}$ exigée par la définition GMM-NHMM).
> La vraie Strategy A livrée est **2-stage** : (1) fit GMM-HMM base, (2)
> NHMM logit sur les états macro. C'est mathématiquement exact à la
> définition GMM-NHMM, contrairement à la K·M expansion qui aurait été un
> sur-modèle. Le module est `src/hmm_core/gmm_nhmm.py`, l'API publique
> `fit_gmm_nhmm()` + `GMMNHMMFittedModel`.

> Document de spec. Pour le contexte stratégique, voir
> [docs/roadmap.md § Phase A.10](../roadmap.md).

---

## 1. Contexte et motivation

### Le besoin moteur (cas crypto)

Le dashboard crypto de Robin (Phase D) modélise des régimes de marché
Bitcoin via NHMM. Aujourd'hui, le modèle force un dilemme :

- **Option 1** : un régime "bull" unique → perte d'information sur les
  sous-modes (impossible de distinguer une montée régulière d'un squeeze
  explosif, ces deux comportements sont fondus dans une même Gaussienne).
- **Option 2** : deux régimes "bull-smooth" et "bull-explosive" séparés →
  la transition bull-smooth → bull-explosive est modélisée comme une
  *transition de régime*, ce qui dilue la sémantique (en réalité c'est un
  changement de sous-mode au sein du régime "bull", pas un changement de
  régime macro).

**Aucune des deux options ne reflète la structure du marché**. La structure
naturelle est : un régime macro (bull / bear / range) qui héberge plusieurs
sous-modes (smooth / volatile / squeeze / capitulation).

GMM-NHMM modélise cette hiérarchie correctement : chaque régime héberge un
GMM en émission qui capture les sous-modes, tandis que les transitions
entre régimes restent covariate-dependent.

### Pourquoi maintenant

- A.1 (NHMM) et A.5 (HMMBackend abstraction) sont livrés : les
  prérequis techniques sont là.
- V (validation suite) sera livré juste avant A.10 : le filet pour
  valider la math est prêt.
- Phase D (dashboard crypto) reste le canary permanent : c'est
  l'endroit où A.10 prouvera sa valeur.
- Le wedge "interpretability-mandate" (quant finance, recherche
  académique) est exactement le segment qui demande GMM-NHMM.

### Pourquoi c'est notre wedge

Audit 2026-05-22 : aucun outil Python ne fait GMM-NHMM proprement.
- `hmmlearn` GMMHMM : GMM oui, NHMM non
- `sequentia` : GMM oui, NHMM non
- IOHMM (Mogeng/GitHub) : NHMM oui, GMM non
- GaussianIOHMM : NHMM + Gaussian, GMM en placeholder
- R `NHMM` (CRAN) : a tout, mais R (hors stack Python)

Notre opportunité de différenciation est concrète et défensible.

## 2. Formulation mathématique

### Notations

- $T$ : longueur de la séquence d'observations
- $K$ : nombre d'états (régimes), e.g. K=3 pour {bear, range, bull}
- $M$ : nombre de composantes GMM par état, e.g. M=2 pour {smooth, explosive}
- $D$ : dimension de l'observation
- $P$ : nombre de covariates
- $z_t \in \{1, \dots, K\}$ : état latent (régime) à $t$
- $c_t \in \{1, \dots, M\}$ : composante de mixture à $t$ (latente aussi)
- $x_t \in \mathbb{R}^D$ : observation à $t$
- $u_t \in \mathbb{R}^P$ : covariates à $t$ (e.g. funding rate, vol réalisée, volume)

### Le modèle

**État initial** :
$$\pi_k = P(z_1 = k)$$

**Transitions covariate-dependent** (multinomial logit, hérité de NHMM A.1) :
$$A_{ij}(u_t) = P(z_t = j \mid z_{t-1} = i, u_t) = \frac{\exp(\beta_{ij}^\top u_t)}{\sum_{j'=1}^K \exp(\beta_{ij'}^\top u_t)}$$
avec $\beta_{ij} \in \mathbb{R}^P$, et la convention $\beta_{iK} = 0$
(reference category) pour l'identifiabilité.

**Émission GMM par état** :
$$p(x_t \mid z_t = k) = \sum_{m=1}^M w_{km} \, \mathcal{N}(x_t \mid \mu_{km}, \Sigma_{km})$$
avec $\sum_m w_{km} = 1$ pour chaque $k$.

**Likelihood complète** (données complètes, $z$ et $c$ observés) :
$$p(z, c, x \mid u) = \pi_{z_1} \prod_{t=2}^T A_{z_{t-1}, z_t}(u_t) \prod_{t=1}^T w_{z_t, c_t} \mathcal{N}(x_t \mid \mu_{z_t, c_t}, \Sigma_{z_t, c_t})$$

### Inférence : EM avec deux niveaux de latence

**E-step** : calculer
- $\gamma_t(k) = P(z_t = k \mid x_{1:T}, u_{1:T})$ — posterior marginal d'état
- $\xi_t(k, m) = P(z_t = k, c_t = m \mid x_{1:T}, u_{1:T})$ — posterior joint d'état + composante
- $\zeta_t(i, j) = P(z_{t-1} = i, z_t = j \mid x_{1:T}, u_{1:T})$ — posterior transition

Forward-backward standard sur le HMM, mais avec :
$$b_k(x_t) = \sum_{m=1}^M w_{km} \mathcal{N}(x_t \mid \mu_{km}, \Sigma_{km})$$
comme densité d'émission par état (marginal sur $c_t$).

Puis $P(c_t = m \mid z_t = k, x_t) = \frac{w_{km} \mathcal{N}(x_t \mid \mu_{km}, \Sigma_{km})}{b_k(x_t)}$.

D'où $\xi_t(k, m) = \gamma_t(k) \cdot P(c_t = m \mid z_t = k, x_t)$.

**M-step** :
- $w_{km}^{new} = \frac{\sum_t \xi_t(k, m)}{\sum_t \gamma_t(k)}$
- $\mu_{km}^{new} = \frac{\sum_t \xi_t(k, m) x_t}{\sum_t \xi_t(k, m)}$
- $\Sigma_{km}^{new} = \frac{\sum_t \xi_t(k, m) (x_t - \mu_{km}^{new})(x_t - \mu_{km}^{new})^\top}{\sum_t \xi_t(k, m)}$
- $\beta_{ij}^{new}$ : régression logistique multinomiale pondérée par
  $\zeta_t(i, j)$ — exactement ce qui est fait déjà dans A.1 NHMM, on
  réutilise.

### Équivalence K·M ↔ Stratégie A

Le modèle GMM-NHMM est mathématiquement équivalent à un **HMM à $K \cdot M$
états avec émission gaussienne pure**, sous contraintes structurelles :

1. La matrice de transition $K M \times K M$ a une structure **block** : la
   transition de l'état $(i, p)$ vers $(j, q)$ ne dépend pas de $p$ ni de
   $q$ pour la partie "régime macro" :
   $$A_{(i,p),(j,q)} = A_{ij} \cdot w_{jq}$$
   c'est-à-dire : on transit d'abord vers le régime $j$ selon $A_{ij}(u_t)$
   (NHMM standard), puis on entre dans la composante $q$ avec probabilité
   $w_{jq}$.

2. Le mask `topology.transition_mask()` peut encoder cette structure
   block en posant les transitions "régime-régime" et en imposant les
   contraintes par ligne.

Cette équivalence justifie la **Stratégie A** ci-dessous.

## 3. Stratégies d'implémentation — historique et version livrée

> **Découverte d'implémentation 2026-05-22 PM** : la rédaction initiale du
> spec proposait une Strategy A basée sur "expansion K·M en HMM Gaussien"
> avec contrainte sur la matrice de transition via mask block-structured.
> Cette approche s'est révélée **incorrecte** : la NHMM logit aurait
> $K \cdot M$ outcomes par état source, donc $(K \cdot M)^2 \cdot P$
> coefficients libres SANS contrainte de factorisation
> $A_{ij}(u_t) \cdot w_{jq}$. Le modèle obtenu serait sur-paramétré par
> rapport à GMM-NHMM strict (section 2).
>
> La **Strategy A livrée** est **2-stage**, qui correspond exactement à
> la définition section 2 : (1) fit GMM-HMM base = w/μ/Σ statiques, (2)
> NHMM logit sur les états macro = A_{ij}(u_t). Code dans
> `src/hmm_core/gmm_nhmm.py`. Implémentation triviale grâce à A.1 + A.5.

## 3bis. Stratégies retenues (livrées)

### Stratégie A — Expansion K·M (MVP)

**Principe** : pas de nouveau code de fond. On exploite l'équivalence.

**Implémentation** :
1. Si l'utilisateur déclare `emission.type='gmm'` + `transitions.type='covariate'`
   (et fournit `covariates`), notre dispatcher détecte le cas GMM-NHMM
2. En interne, construit une **topologie K·M-état Gaussienne** :
   - États : $(k, m)$ pour $k \in [K], m \in [M]$
   - Mask : transition autorisée $(i,p) \to (j,q)$ ssi le mask original
     autorise $i \to j$ (les composantes peuvent toutes co-exister par défaut)
   - Émission : Gaussienne par sous-état, init via GMM init strategy
3. Appelle le backend NHMM existant sur cette topologie étendue
4. Reconstruit l'output GMM-NHMM à partir du fit K·M-état :
   - $A^{regime}_{ij}$ par agrégation des transitions de bloc
   - $w_{km}, \mu_{km}, \Sigma_{km}$ par lecture directe des $(k, m)$ sous-états

**Avantages** :
- Réutilise tout le code A.1 NHMM existant
- 3-5 jours d'effort
- Cohérent avec notre patron "ship pragmatique, refactor à la demande"

**Inconvénients** :
- Décodage Viterbi retourne des $(k, m)$ qu'il faut projeter sur $k$ pour l'utilisateur
- Espace d'états $K \cdot M$ peut devenir gros (K=4, M=3 → 12 sous-états)
- BIC nominal moins informatif (compte les params du modèle équivalent étendu)

### Stratégie B — GMM-NHMM direct (refactor optionnel)

**Principe** : E-step et M-step explicites, gérés en pur numpy dans un
nouveau backend `NumpyGMMNHMMBackend`.

**Implémentation** :
1. `backends/gmm_nhmm_backend.py` : nouvelle classe implémentant le
   protocole `HMMBackend` (fit, decode, predict_proba, score)
2. Forward-backward log-space sur le HMM macro (K états)
3. E-step calcule explicitement $\gamma, \xi, \zeta$ avec mixture
4. M-step met à jour $(w, \mu, \Sigma)$ par état directement et $\beta$
   via régression logistique pondérée
5. Conversion entre Topology(GMM, NHMM) et état interne du backend

**Avantages** :
- Décodage Viterbi natif sur $K$ états (sémantique propre pour l'utilisateur)
- BIC correct comptant exactement les params du modèle
- Plus efficace numériquement (pas de blow-up d'états)
- Permet de remplir une vraie pièce manquante de l'écosystème Python

**Inconvénients** :
- ~1 semaine d'effort additionnel
- Plus de surface à valider scientifiquement
- Premier backend qui ne délègue PAS à hmmlearn (mais c'est aussi ce qui
  rapporte enfin l'investissement A.5)

### Stratégie C — Hybride (recommandée)

Phase MVP : Stratégie A (livre la fonctionnalité utilisateur).
Phase validation : Stratégie B livrée en parallèle, utilisée comme
*référence indépendante* pour V.5 cross-check.

Si V.5 valide que A ≡ B numériquement → garder A comme implémentation
canonique, B comme oracle pour les futures évolutions.
Si V.5 révèle que A est limitée → migrer vers B comme implémentation canonique.

## 4. API publique

### YAML topologie étendue

```yaml
name: btc_regimes_with_submodes
n_states: 3                      # K: 3 régimes macro
state_names: [bear, range, bull]
emission:
  type: gmm                      # ← émission GMM par état
  covariance_type: full
  n_features: 1                  # log-returns
  n_mix: 2                       # M: 2 sous-modes par régime
transitions:
  type: covariate                # ← transitions NHMM
  covariates: [funding_rate, realized_vol, volume_z]
startprob: uniform
init:
  strategy: kmeans
  seed: 42
fit:
  algorithm: baum_welch
  n_iter: 200
  tol: 1.0e-4
  regularization: 0.01           # L2 sur coefficients β
```

### Python API

```python
from hmm_core.fit import fit
from hmm_core.io import load_topology
import pandas as pd

topo = load_topology("btc_regimes.yaml")
X = pd.read_csv("btc_returns.csv").to_numpy()
covariates = pd.read_csv("btc_features.csv").to_numpy()

result = fit(topo, X, covariates=covariates)

# Accès aux sous-modes
print(result.model.weights_)          # (K, M) — poids des composantes
print(result.model.means_)            # (K, M, D) — moyennes par sous-mode
print(result.model.covars_)           # (K, M, D, D) — covariances par sous-mode

# Décodage régime macro (projeté sur K)
backend = get_backend()
regime_path = backend.decode(result.model, X, covariates=covariates)  # (T,) in [0, K)

# Décodage joint (K·M) pour analyse sous-mode
joint_path = backend.decode_joint(result.model, X, covariates=covariates)  # (T, 2) → (k, m)
```

### CLI extension

```bash
hmm-fit run btc_regimes.yaml btc_returns.csv \
    --covariates btc_features.csv \
    --output results/btc_gmm_nhmm

hmm-fit show results/btc_gmm_nhmm/model.pkl
# Affiche : K=3, M=2, log-lik, BIC, transitions moyennes, sous-modes par état
```

## 5. Tests (intégrés dans suite normale + V.5)

### Tests unitaires standard (`tests/test_gmm_nhmm.py`)

| Test | Vérifie |
|---|---|
| `test_gmm_nhmm_topology_validates` | YAML avec `emission.type=gmm` + `transitions.type=covariate` valide |
| `test_gmm_nhmm_kxm_expansion_correct` | La topologie expansée K·M a le bon mask block |
| `test_gmm_nhmm_fit_converges` | EM converge en < n_iter sur jouet |
| `test_gmm_nhmm_recovers_synthetic` | Sur données générées avec params connus (K=2, M=2), recovers à 10 % près |
| `test_gmm_nhmm_decode_projects_to_K` | `decode()` retourne $\in [0, K)$, pas $[0, K \cdot M)$ |
| `test_gmm_nhmm_decode_joint_returns_KM` | `decode_joint()` retourne $(k, m)$ |
| `test_gmm_nhmm_handles_covariates_shape` | Erreur explicite si covariates.shape ≠ (T, P) |
| `test_gmm_nhmm_BIC_penalizes_correctly` | BIC compte les vrais params (pas K·M étendu) |
| `test_gmm_nhmm_label_switching_robust` | Multi-start retourne des params permutationally-équivalents |
| `test_gmm_nhmm_constrains_K_max_4_M_max_3` | Warning explicite si K>4 ou M>3 (sur-paramétrisation) |

### Tests Phase V.5 (validation cross-check)

| Test | Vérifie |
|---|---|
| `test_v5_strategy_A_equiv_strategy_B_K2M2` | Sur jouet K=2 M=2, Stratégies A et B donnent log-lik identique à 1e-6 |
| `test_v5_strategy_A_equiv_strategy_B_K3M2` | Idem K=3 M=2 |
| `test_v5_decoding_consistency_A_B` | Viterbi des deux stratégies match à 100 % |
| `test_v5_BIC_consistency_A_B` | BIC des deux stratégies match à 1e-6 |

## 6. Limites d'identifiabilité (critique)

GMM-NHMM est un modèle riche, et facilement sur-paramétré. Le spec
documente explicitement les limites :

### Recommandations utilisateur (warnings dans le code)

- $K \leq 4$ : au-delà, identifiabilité des régimes devient fragile
- $M \leq 3$ : au-delà, les composantes intra-régime deviennent
  indistinguables
- $P \leq 6$ : au-delà, les coefficients $\beta_{ij}$ sont difficilement
  identifiables sur < 5000 observations
- $T \geq 200 \cdot \text{free\_params}$ : règle empirique pour stabilité

### Régularisation par défaut

- L2 sur $\beta_{ij}$ : pénalité $\lambda_\beta = 0.01$
- Floor sur covariances : $\Sigma_{km} \mathrel{+}= 10^{-3} I$
- Smoothing Dirichlet sur poids : $w_{km} \mathrel{+}= 10^{-6}$

### Sélection $(K, M)$

- Recommander BIC strict
- Comparer GMM-NHMM(K, M) vs NHMM(K) standard : si BIC(GMM-NHMM) <
  BIC(NHMM), c'est une preuve qu'il y a des sous-modes
- Inversement, si BIC(NHMM) ≤ BIC(GMM-NHMM), simplifier vers NHMM

### Identifying constraints

Pour bypass le label switching :
1. États ordonnés par $\mu_{k, 1}$ croissant (composante de base)
2. Composantes au sein d'un état ordonnées par poids $w_{km}$ décroissant

Ces contraintes sont appliquées en post-fit, pas durant EM.

## 7. Intégration dashboard crypto (Phase D)

A.10 doit être validé sur le cas d'usage réel :

1. Adapter le YAML crypto existant pour exposer `emission.type=gmm`
2. Fitter GMM-NHMM(K=3, M=2) vs NHMM(K=3) standard sur 5 ans BTC daily
3. Comparer BIC, AIC, log-likelihood
4. Comparer interpretation des régimes (régression manuelle par
   Robin pour validation domaine)
5. Si gain significatif (> 5 points BIC) → A.10 est validé en
   production sur ce dataset

C'est le test ultime — pas un test unitaire, un test produit.

## 8. Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Stratégie A et B divergent sur cas extrêmes | Moyenne | V.5 cross-check obligatoire avant ship |
| EM convergence lente (deux niveaux de latence) | Moyenne | Multi-start (10 init aléatoires), max_iter=500 par défaut |
| Sur-paramétrisation silencieuse pour user | Élevée | Warning explicite si T < 200 · params, ou si BIC favorise NHMM simple |
| Label switching crée des résultats non-reproductibles | Moyenne | Identifying constraints + tests dédiés |
| Décodage Viterbi K·M lent pour grand K·M | Faible | Limite explicite K=4, M=3 → max 12 sous-états, OK |
| API confuse (deux niveaux de paramètres) | Moyenne | Documentation extensive + exemple crypto canonique + leçon Academy dédiée (E.4 ?) |
| Pas de gain BIC vs NHMM sur cas réels Robin | Faible | Si c'est le cas, A.10 reste utile pour le wedge "interpretability", on documente l'absence de gain et on laisse l'utilisateur décider |

## 9. Définition de "done" pour A.10

- [ ] Topology accepte `emission.type=gmm` + `transitions.type=covariate` simultanés (validation YAML + Python)
- [ ] Stratégie A (K·M expansion) implémentée dans dispatcher `fit()`
- [ ] Stratégie B (`NumpyGMMNHMMBackend`) implémentée et enregistrée comme backend optionnel via `backend='gmm-nhmm-direct'`
- [ ] 10 tests unitaires dans `tests/test_gmm_nhmm.py`, tous passent
- [ ] 4 tests V.5 dans `validation/test_v5_gmm_nhmm.py`, tous passent
- [ ] Section README dédiée avec exemple crypto canonique
- [ ] Notebook example dans `examples/btc_gmm_nhmm.ipynb` (optionnel mais recommandé pour marketing)
- [ ] ADR-0008 : pourquoi Stratégie C hybride
- [ ] Validation produit sur dashboard crypto : gain BIC documenté ou absence de gain documentée

## 10. Successeurs hors-scope

Listés pour anti-scope-creep :

- **A.10.1** Bayesian GMM-NHMM : intersection avec A.6 (gated)
- **A.10.2** GMM-NHMM avec composantes dépendantes des covariates (poids
  $w_{km}(u_t)$ aussi covariate-dependent) — recherche, très exotique
- **A.10.3** Skew-Normal mixtures pour capter asymétrie des returns —
  potentiellement intéressant pour crypto mais pas urgent
- **A.10.4** Auto-regressive GMM-NHMM (returns dépendent de $x_{t-1}$
  conditionnellement à l'état) — combine avec littérature MS-AR

Aucune de ces extensions n'est promise. Chacune attend un signal réel
(papier publié, demande utilisateur, blocage cas d'usage).

## 11. ADR à créer

`docs/decisions/0008-gmm-nhmm-strategy-c-hybrid.md` :
- Pourquoi Stratégie C plutôt que A seule ou B seule ?
- Pourquoi NumpyGMMNHMMBackend et pas hmmlearn-based ?
- Pourquoi limites $K \leq 4$, $M \leq 3$ comme défauts ?
- Comment ajouter une stratégie D future (e.g. variational) ?

## 12. Références scientifiques

- **Bengio & Frasconi 1995** — Input-Output HMM original
- **Pouzo 2022 (Econometrica)** — "Maximum Likelihood Estimation in Markov
  Regime-Switching Models With Covariate-Dependent Transition
  Probabilities" — théorie ML formelle, consistance, normalité asymptotique
- **NHMM Bayesian via Polya-Gamma** (arXiv:1701.02856) — formulation
  Bayésienne efficace pour le futur A.10.1 si A.6 ship
- **R package `NHMM`** (CRAN) — implémentation R complète à benchmarker
  contre la nôtre dans V.5
- **Diebold, Lee & Weinbach 1994** — TVTP en Markov-switching, origine économétrique
- **Markov-Switching State-Dependent TVTP** (ScienceDirect 2021) — flag
  les difficultés d'identification multi-régime
- **Non-Homogeneous MS-GAMLSS** (arXiv:2601.03760, 2026) — extension
  récente, à consulter pour comparaison
