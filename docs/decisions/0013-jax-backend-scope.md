# ADR-0013 : JaxBackend — wrap dynamax (code gated sur signal)

**Status** : SPEC-ONLY · code **GATED**
**Date** : 2026-05-26
**Related** : [ADR-0003 backend abstraction](0003-backend-abstraction.md), [ADR-0012 distribution strategy hybrid](0012-distribution-strategy-hybrid.md)

## Contexte

Le `HMMBackend` Protocol (ADR-0003) a été designé exactement pour
permettre la substitution du moteur d'inférence sans casser le reste
de `hmm_core`. Trois backends concrets ont été ou sont envisagés :

1. `HmmlearnBackend` (livré v0.1, défaut) — CPU, Cython, basé sur
   hmmlearn. Fonctionne, mais bottleneck à grand `T`.
2. `BayesianHMMBackend` (livré A.6, optionnel via `[bayesian]`
   extra) — PyMC NUTS, CPU. Donne des credible intervals mais lent.
3. `JaxBackend` — **objet de cette ADR**. Wrap autour de
   [`dynamax`](https://github.com/probml/dynamax) (Murphy lab) pour
   exposer une inférence HMM GPU/TPU-accelerated via JAX.

### Pourquoi cette ADR existe

Quatre signaux pourraient un jour déclencher l'implémentation :

1. **Demande externe explicite** — issue GitHub ou email d'un user
   qui dit avoir besoin de GPU/JAX HMM training.
2. **Pain interne Robin-driven** — un use case (e.g. crypto avec
   plus de signaux on-chain) dépasse `T = 100 000` timesteps de
   façon récurrente, OU un Baum-Welch réel prend > 10 min.
3. **Bayesian backend devient ingérable** — `BayesianHMMBackend`
   NUTS sampling prend > 30 min sur un cas typique. Migrer vers
   `numpyro` (Bayesian-JAX-native) deviendrait justifié.
4. **Concurrence prend le wedge** — une autre lib HMM ship du GPU
   acceleration et devient la référence Python ML. Réactif plutôt
   que proactif.

Tant qu'aucun des quatre n'est fired, l'ADR reste documentation et
le code n'est pas écrit. Discipline cohérente avec
[ADR-0012](0012-distribution-strategy-hybrid.md) (HMM specialist, pas
sandbox générique) et la scope discipline du projet (refus pivot
HMM/SSM/Transformer).

## Décision

### Architecture

`hmm_core.backends.jax_backend.JaxBackend` **wrap** dynamax via le
`HMMBackend` Protocol. Pas de fork upstream à l'origine — option fork
explicitement différée (voir « Alternatives rejetées »).

```
hmm_core.backends.jax_backend.JaxBackend
    ├── implements HMMBackend Protocol (ADR-0003)
    ├── wraps dynamax.hidden_markov_model.{GaussianHMM,
    │         CategoricalHMM, GaussianMixtureHMM}
    ├── injects constrained-mask projection APRÈS chaque dynamax M-step
    │   (~30 LOC de jnp + @jax.jit)
    └── NotImplementedError clair sur :
        - emission.type == "poisson"  (dynamax ne le supporte pas
          natif, fallback HmmlearnBackend)
        - variants NHMM / Factorial / Hierarchical
          (à ouvrir comme sub-ADRs si demandé)
```

### Constrained mask en JAX (la vraie valeur ajoutée)

dynamax fait du Baum-Welch standard sur `transmat` libre. NOTRE
contribution = forcer les zéros structurels imposés par
`topology.allowed_transitions`. Implémentation visée :

```python
@jax.jit
def project_to_masked_simplex(
    transmat: jnp.ndarray, mask: jnp.ndarray
) -> jnp.ndarray:
    """Force transmat[i,j] = 0 où mask[i,j] is False, renormalise rows."""
    masked = jnp.where(mask, transmat, 0.0)
    return masked / masked.sum(axis=1, keepdims=True)
```

Appelé après chaque M-step de dynamax (via leur hook
`params_update_fn` ou équivalent — à confirmer à l'impl).

### API user-facing

Réutilise le pattern A.6 BayesianHMMBackend — **pas de nouveau
design** :

```python
from hmm_core.backends import get_backend
backend = get_backend("jax")
result = backend.fit(topology, X, ...)
```

### Scope v1 (si on l'implémente)

| Emission | v1 | Raison |
|---|---|---|
| Gaussian | ✅ | dynamax `GaussianHMM` |
| GMM | ✅ | dynamax `GaussianMixtureHMM` |
| Multinomial | ✅ | dynamax `CategoricalHMM` |
| Poisson | ❌ → fallback HmmlearnBackend | dynamax pas de support natif |
| Variants NHMM / Factorial / HHMM | ❌ → sub-ADRs si signal | non couverts par dynamax |

### Distribution

```toml
# pyproject.toml [project.optional-dependencies]
jax = [
    "jax>=0.4.30",
    "jaxlib>=0.4.30",
    "dynamax>=0.1.5",
]
```

User : `pip install "hmm-studio[jax]"`. Pour CUDA : doc README
`pip install jax[cuda12_pip]` — on n'ajoute pas de complexité
packaging, l'user gère son driver / version cuda.

### Performance contract

À mesurer empiriquement à l'impl :
- JaxBackend doit **battre** HmmlearnBackend sur `T ≥ 50k` (Gaussian).
- Et `T ≥ 10k` (GMM).
- En-dessous, JIT compilation overhead domine ; on documente
  « use HmmlearnBackend for small T » et JaxBackend n'est pas
  recommandé.
- **Si le contrat échoue** : le code n'est pas mergé, l'ADR le
  consigne (« perf contract failed, JaxBackend abandoned »).

### Validation — V.7 cross-check

Nouvelle suite validation à créer :

- `validation/test_v7_jax_backend_cross_check.py`
- 5+ datasets (synthetic Gaussian, Multinomial, GMM)
- Assertion : `|JaxBackend.log_likelihood - HmmlearnBackend.log_likelihood| < 1e-6`
- Assertion : transmat agreement à 1e-8 après mask projection

## Conséquences

### Positives

- Wedge « deepest HMM library in the Python scientific stack »
  (ADR-0012) tient face à de futures libs GPU.
- BayesianHMMBackend a une voie d'accélération via numpyro si demandé.
- Le HMMBackend Protocol (ADR-0003) prouve sa valeur pour la **3ème
  fois** — design validé empiriquement.

### Négatives / coût accepté

- Une dépendance optionnelle de plus à monitorer (dynamax + jax).
- Si dynamax meurt, on devra forker ou réécrire — risque assumé.
- Surface d'API plus grande pour les users (3 backends à comprendre).
- Test matrix CI explose (CPU / Linux / Windows / Mac, + GPU si on
  veut le tester réellement).

### Réversibilité

Si JaxBackend devient insoutenable, on le retire en marquant
`DEPRECATED` dans le module, on garde l'ADR, on supprime le code.
Aucun user n'est cassé tant qu'ils utilisent le défaut
`HmmlearnBackend`. La spec sert d'archive (« voici pourquoi on a
essayé, voici pourquoi on a abandonné »).

## Alternatives rejetées

| Alternative | Pourquoi rejetée |
|---|---|
| **Custom JAX from scratch** | 800-1500 LOC à maintenir, réinvente ce que dynamax fait déjà propre. Justifié seulement si on veut le wedge « la lib HMM JAX la plus propre » — pas notre wedge (ADR-0012). |
| **Fork dynamax + patch** | Patches seraient architecturaux (mask, NHMM, Poisson) plutôt que chirurgicaux comme le pattern GitNexus. Drift upstream rapide, distribution PyPI un cauchemar (vendoring vs package séparé `RoJLD/dynamax-patched`). **Différé** : à reconsidérer si dynamax bloque sur un cas critique (NHMM en JAX par exemple). |
| **Unsloth integration** (proposé 2026-05-26) | Différent paradigme (LLM transformer finetuning), zéro chevauchement technique avec HMM. Violerait scope discipline (refus pivot HMM/SSM/Transformer décidé 2026-05-22). |
| **TFP `tfp.distributions.HiddenMarkovModel`** | TFP HMM est moins actif que dynamax depuis 2022, abandonné en pratique par Google. dynamax est le standard de fait pour HMM-en-JAX. |
| **pomegranate** | C++ avec bindings Python. Pas de support GPU natif. Pas de gain vs hmmlearn pour notre use case. |

## Revisit triggers (gating détaillé)

L'implémentation commence dès qu'**au moins un** trigger est satisfait :

1. **Signal externe explicite** — issue GitHub ou email d'un user
   qui dit « j'ai besoin de GPU/JAX HMM training pour mon dataset ».
   Pas de drive-by ; il faut une description de use case sérieuse.
2. **Pain interne Robin-driven** — use case Robin dépasse `T = 100k`
   **de façon récurrente** (3+ fits différents, pas un one-off) OU
   un Baum-Welch réel sur use case typique prend > 10 min sur CPU.
3. **Bayesian backend trop lent** — `BayesianHMMBackend` NUTS prend
   > 30 min sur un cas typique. Migrer vers numpyro deviendrait
   justifié.
4. **Concurrence prend le wedge** — une lib HMM concurrente ship du
   GPU acceleration et devient la référence Python ML (ex : si
   `hmmlearn` upstream intègre JAX directement, on s'aligne ; si une
   nouvelle lib gagne).

Si aucun trigger n'est fired à M+6 mois depuis cette ADR (2026-11-26),
on revisite : faut-il maintenir cette ADR active, la marquer
DEFERRED, ou la fermer comme « not pursuing » ?

## Pointeurs

- `src/hmm_core/backends/_protocol.py` — `HMMBackend` Protocol définition (ADR-0003)
- `src/hmm_core/backends/hmmlearn_backend.py` — default impl
- `src/hmm_core/backends/bayesian_backend.py` — A.6, optional via `[bayesian]` extra
- [dynamax repo (Murphy lab)](https://github.com/probml/dynamax)
- [Murphy MLAPP Ch. 17-18](https://archive.org/details/machinelearningp0000murp) — HMM + SSM theory en perspective Bayesienne
- [ADR-0012 — distribution strategy hybrid](0012-distribution-strategy-hybrid.md) — wedge HMM specialist
- Memory note `hmm-studio scope discipline` — refus pivot HMM/SSM/Transformer (2026-05-22)
